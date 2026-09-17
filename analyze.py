"""Turn results.json into the numbers that go in the README.

    python analyze.py --run results/pilot            # automatic claim checks
    python analyze.py --run results/pilot --ratings results/pilot/ratings

Automatic metrics (per condition):
  claims                how many claims the model made
  checkable             share of claims the log can judge at all
  supported             share of checkable claims that match a logged event
  contradicted          share with no such event by that player that minute
  wrong time            right kind of event, wrong moment (>3 s off)
  delivery count error  mean |claimed - actual| soups per minute

Human ratings, if present, are pairwise: which of two reviews of the same
episode is more accurate, and which is more useful.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def automatic_metrics(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in records:
        for condition, block in rec["conditions"].items():
            acc = out.setdefault(
                condition,
                {
                    "claims": 0,
                    "status": Counter(),
                    "types": defaultdict(Counter),
                    "delivery_err": [],
                    "parse_failures": 0,
                    "named_player": 0,
                    "named_status": Counter(),
                    "round_time": 0,
                    "timed": 0,
                },
            )
            for seg in block["segments"]:
                acc["parse_failures"] += bool(seg.get("parse_failed"))
                if seg.get("deliveries_claimed") is not None:
                    acc["delivery_err"].append(abs(seg["deliveries_claimed"] - seg["deliveries_true"]))
                for claim in seg["claims"]:
                    status = claim["verdict"]["status"]
                    acc["claims"] += 1
                    acc["status"][status] += 1
                    acc["types"][claim.get("type", "other")][status] += 1
                    named = claim.get("player") in {"P1", "P2"}
                    acc["named_player"] += named
                    if named:  # a claim about "both players" is much easier to be right about
                        acc["named_status"][status] += 1
                    if claim.get("time") is not None:
                        acc["round_time"] += float(claim["time"]) % 5 == 0
                        acc["timed"] += 1

    summary = {}
    for condition, acc in out.items():
        checkable = acc["claims"] - acc["status"]["unchecked"]
        named_checkable = acc["named_player"] - acc["named_status"]["unchecked"]
        summary[condition] = {
            "claims": acc["claims"],
            "checkable": checkable,
            "checkable_share": round(checkable / acc["claims"], 3) if acc["claims"] else None,
            "supported": round(acc["status"]["supported"] / checkable, 3) if checkable else None,
            "contradicted": round(acc["status"]["contradicted"] / checkable, 3) if checkable else None,
            "wrong_time": round(acc["status"]["wrong_time"] / checkable, 3) if checkable else None,
            "delivery_count_mae": round(statistics.mean(acc["delivery_err"]), 2) if acc["delivery_err"] else None,
            "named_player_share": round(acc["named_player"] / acc["claims"], 3) if acc["claims"] else None,
            "supported_when_named": round(acc["named_status"]["supported"] / named_checkable, 3)
            if named_checkable
            else None,
            "round_timestamp_share": round(acc["round_time"] / acc["timed"], 3) if acc["timed"] else None,
            "parse_failures": acc["parse_failures"],
            "by_type": {
                t: {"n": sum(c.values()), "supported": c["supported"], "contradicted": c["contradicted"], "wrong_time": c["wrong_time"]}
                for t, c in sorted(acc["types"].items())
            },
        }
    return summary


def rating_metrics(rating_dir: Path) -> dict:
    files = sorted(rating_dir.glob("*.json")) if rating_dir.exists() else []
    if not files:
        return {}
    # votes per pair, so a telemetry-vs-video vote is never mixed with a video-vs-video one
    votes: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    per_rater: dict[str, dict] = {}
    for path in files:
        rater = path.stem
        per_rater[rater] = {}
        for row in json.loads(path.read_text()):
            key = (row["trial_id"], row["pair"], row["question"])
            votes[row["pair"]][row["question"]].append(row["winner"])
            per_rater[rater][str(key)] = row["winner"]

    agreement = None
    if len(per_rater) > 1:
        raters = list(per_rater)
        shared = set.intersection(*[set(per_rater[r]) for r in raters])
        if shared:
            agree = sum(1 for k in shared if len({per_rater[r][k] for r in raters}) == 1)
            agreement = round(agree / len(shared), 3)

    return {
        "raters": len(files),
        "votes": {pair: {q: dict(Counter(v)) for q, v in qs.items()} for pair, qs in votes.items()},
        "unanimous_share": agreement,
    }


def to_markdown(summary: dict, ratings: dict, n_episodes: int) -> str:
    rows = [
        "| condition | claims | supported | supported, naming a player | contradicted | wrong time "
        "| names a player | timestamp on a 5 s grid | delivery count error |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for condition, m in summary.items():
        pct = lambda v: "-" if v is None else f"{v * 100:.0f}%"  # noqa: E731
        rows.append(
            f"| {condition} | {m['claims']} | {pct(m['supported'])} | {pct(m['supported_when_named'])} | "
            f"{pct(m['contradicted'])} | {pct(m['wrong_time'])} | {pct(m['named_player_share'])} | "
            f"{pct(m['round_timestamp_share'])} | "
            f"{'-' if m['delivery_count_mae'] is None else m['delivery_count_mae']} |"
        )
    text = [f"Episodes: {n_episodes}", "", *rows]
    if ratings:
        text += ["", f"Human pairwise ratings from {ratings['raters']} rater(s), votes per question:"]
        for pair, questions in sorted(ratings["votes"].items()):
            text += [f"- {pair}: " + "; ".join(f"{q} {json.dumps(v)}" for q, v in questions.items())]
        if ratings.get("unanimous_share") is not None:
            text += [f"Raters agreed on {ratings['unanimous_share'] * 100:.0f}% of the pairs they both saw."]
    return "\n".join(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("results/run"))
    parser.add_argument("--ratings", type=Path, default=None)
    args = parser.parse_args()

    records = json.loads((args.run / "results.json").read_text())
    summary = automatic_metrics(records)
    ratings = rating_metrics(args.ratings or args.run / "ratings")

    (args.run / "metrics.json").write_text(json.dumps({"automatic": summary, "human": ratings}, indent=2))
    report = to_markdown(summary, ratings, len(records))
    (args.run / "metrics.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
