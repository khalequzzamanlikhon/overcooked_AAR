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

Chance baselines (per condition), so a rate can be read against what a claim
with no real information would score:
  supported at a random time   the same claims, each moved to a random time
                               in its minute and checked again
  not contradicted, swapped    claims naming P1 or P2, re-checked with the
                               player swapped; if this is close to the real
                               rate, the player names carry little information

Human ratings, if present, are pairwise: which of two reviews of the same
episode is more accurate, and which is more useful.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from aar.telemetry_to_text import Event, segment_events
from aar.verify import verify_claim

_SWAP = {"P1": "P2", "P2": "P1"}


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


def chance_baselines(records: list[dict], draws: int = 20, seed: int = 0) -> dict[str, dict]:
    """Re-check every checkable claim with its time or its player scrambled."""
    rng = random.Random(seed)
    acc: dict[str, Counter] = defaultdict(Counter)
    for rec in records:
        events = [Event(**e) for e in rec["events"]]
        for condition, block in rec["conditions"].items():
            a = acc[condition]
            for seg in block["segments"]:
                seg_events = segment_events(events, seg["start"], seg["end"])
                for claim in seg["claims"]:
                    status = claim["verdict"]["status"]
                    if status == "unchecked":
                        continue
                    for _ in range(draws):
                        moved = dict(claim, time=rng.uniform(seg["start"], seg["end"]))
                        a["random_supported"] += verify_claim(moved, seg_events)["status"] == "supported"
                    a["random_draws"] += draws
                    if claim.get("player") in _SWAP:
                        swapped = dict(claim, player=_SWAP[claim["player"]])
                        a["named"] += 1
                        a["named_ok"] += status != "contradicted"
                        a["swapped_ok"] += verify_claim(swapped, seg_events)["status"] != "contradicted"

    ratio = lambda n, d: round(n / d, 3) if d else None  # noqa: E731
    return {
        condition: {
            "supported_at_random_time": ratio(a["random_supported"], a["random_draws"]),
            "not_contradicted_named": ratio(a["named_ok"], a["named"]),
            "not_contradicted_swapped": ratio(a["swapped_ok"], a["named"]),
        }
        for condition, a in acc.items()
    }


_VIDEO_ONLY = {"video_dense", "video_sparse"}


def rating_metrics(rating_dir: Path) -> dict:
    files = sorted(rating_dir.glob("*.json")) if rating_dir.exists() else []
    if not files:
        return {}
    # votes per pair, so a telemetry-vs-video vote is never mixed with a video-vs-video one
    votes: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    per_rater: dict[str, dict] = {}
    units: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))  # question -> unit -> answers
    likert: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))  # dimension -> condition -> scores
    likert_units: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    guesses = Counter()
    for path in files:
        rater = path.stem
        per_rater[rater] = {}
        for row in json.loads(path.read_text()):
            if row["question"].startswith("likert_"):
                dim = row["question"][len("likert_"):]
                likert[dim][row["condition"]].append(row["score"])
                likert_units[dim][f"{row['trial_id']}|{row['condition']}"].append(row["score"])
                continue
            key = (row["trial_id"], row["pair"], row["question"])
            votes[row["pair"]][row["question"]].append(row["winner"])
            per_rater[rater][str(key)] = row["winner"]
            units[row["question"]][f"{row['trial_id']}|{row['pair']}"].append(row["winner"])
            if row["question"] == "source_guess":
                shown = set(row["shown_as"].values())
                video = shown & _VIDEO_ONLY
                if len(video) == 1:  # only a pair with exactly one video-only review has a right answer
                    guesses["n"] += 1
                    guesses["no_idea"] += row["winner"] == "no idea"
                    guesses["correct"] += row["winner"] in video

    agreement = None
    if len(per_rater) > 1:
        raters = list(per_rater)
        shared = set.intersection(*[set(per_rater[r]) for r in raters])
        if shared:
            agree = sum(1 for k in shared if len({per_rater[r][k] for r in raters}) == 1)
            agreement = round(agree / len(shared), 3)

    from aar.stats import krippendorff_alpha

    out = {
        "raters": len(files),
        "votes": {pair: {q: dict(Counter(v)) for q, v in qs.items()} for pair, qs in votes.items()},
        "unanimous_share": agreement,
    }
    if len(per_rater) > 1:
        out["krippendorff_alpha"] = {q: krippendorff_alpha(u) for q, u in units.items()}
        out["krippendorff_alpha"] |= {f"likert_{d}": krippendorff_alpha(u, "interval") for d, u in likert_units.items()}
    if guesses["n"]:
        out["source_guess"] = {"pairs": guesses["n"], "correct": round(guesses["correct"] / guesses["n"], 3),
                               "no_idea": round(guesses["no_idea"] / guesses["n"], 3)}
    if likert:
        out["likert_mean"] = {d: {c: round(statistics.mean(v), 2) for c, v in cs.items()} for d, cs in likert.items()}
    return out


def _pct(v: float | None) -> str:
    return "-" if v is None else f"{v * 100:.0f}%"


def to_markdown(summary: dict, baselines: dict, ratings: dict, n_episodes: int) -> str:
    rows = [
        "| condition | claims | supported | supported, naming a player | contradicted | wrong time "
        "| names a player | timestamp on a 5 s grid | delivery count error |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for condition, m in summary.items():
        rows.append(
            f"| {condition} | {m['claims']} | {_pct(m['supported'])} | {_pct(m['supported_when_named'])} | "
            f"{_pct(m['contradicted'])} | {_pct(m['wrong_time'])} | {_pct(m['named_player_share'])} | "
            f"{_pct(m['round_timestamp_share'])} | "
            f"{'-' if m['delivery_count_mae'] is None else m['delivery_count_mae']} |"
        )
    text = [f"Episodes: {n_episodes}", "", *rows]
    text += [
        "",
        "A whole-second timestamp lands on a 5 s grid 20% of the time by chance.",
        "",
        "Chance baselines: the same claims with the time moved to a random moment in",
        "the minute, and with P1 and P2 swapped.",
        "",
        "| condition | supported | supported at a random time | not contradicted (named player) "
        "| not contradicted, P1/P2 swapped |",
        "|---|---|---|---|---|",
    ]
    for condition, b in baselines.items():
        text.append(
            f"| {condition} | {_pct(summary[condition]['supported'])} | {_pct(b['supported_at_random_time'])} | "
            f"{_pct(b['not_contradicted_named'])} | {_pct(b['not_contradicted_swapped'])} |"
        )
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
    parser.add_argument("--legacy-only", action="store_true", help="only the pilot's metrics.json/md")
    parser.add_argument("--no-legacy", action="store_true", help="only the study-v2 metrics")
    parser.add_argument("--out", type=Path, default=None, help="where the v2 files go (default: --run)")
    args = parser.parse_args()

    records = json.loads((args.run / "results.json").read_text())
    if not args.no_legacy:
        # the pilot's scorer, unchanged, so the README's pilot numbers can be regenerated exactly
        summary = automatic_metrics(records)
        baselines = chance_baselines(records)
        ratings = rating_metrics(args.ratings or args.run / "ratings")
        (args.run / "metrics.json").write_text(
            json.dumps({"automatic": summary, "chance": baselines, "human": ratings}, indent=2)
        )
        report = to_markdown(summary, baselines, ratings, len(records))
        (args.run / "metrics.md").write_text(report)
        print(report)
    if args.legacy_only:
        return

    from aar.config import CLAIM_CAP_PILOT
    from aar.report_v2 import write

    config_path = args.run / "config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    cap = config.get("claim_cap", CLAIM_CAP_PILOT)  # the pilot's config predates the field; it used 8
    out = args.out or args.run
    out.mkdir(parents=True, exist_ok=True)
    name = config.get("model", "?").split("/")[-1] + (" 4-bit" if config.get("load_in_4bit") or
                                                        config.get("precision") == "nf4-4bit" else "")
    write(records, out, cap, title=f"Study v2 metrics: {args.run.name} ({name})")
    pilot = [r for r in records if r.get("pilot_subset", True)]
    if 0 < len(pilot) < len(records):
        write(pilot, out, cap, suffix="_pilot15", title=f"Study v2 metrics, pilot's 15 episodes: {args.run.name}")
    print(f"\nstudy-v2 metrics -> {out / 'metrics_v2.md'}")


if __name__ == "__main__":
    main()
