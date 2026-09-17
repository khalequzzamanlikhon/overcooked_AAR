"""Blind pairwise rating of the generated reviews.

Ranking is easier than rating: asking "which of these two is more accurate"
gives a cleaner signal than asking two people to put a 1-5 number on each one,
because they do not have to agree on what a 4 means.

Each rater watches the episode video, then sees two reviews of it as A and B,
in a random order, with the source hidden, and picks one. They are also asked
to guess which one came from the video -- if raters can tell, the comparison is
not really blind and that has to be reported.

    python rate_aars.py --run results/pilot --rater alice
    python rate_aars.py --run results/pilot --rater alice --pairs telemetry:video_dense

By default every pair of conditions is shown (15 episodes x 3 pairs = 45
comparisons, about 3 hours). --pairs limits it to the comparisons you name,
e.g. telemetry:video_dense alone is 15 comparisons, about an hour.

Writes results/pilot/ratings/alice.json. One file per rater, so nobody
overwrites anybody.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

_QUESTIONS = [
    ("accuracy", "Which review describes what actually happened more accurately? [a/b/tie] "),
    ("usefulness", "Which would help this team more next time? [a/b/tie] "),
]
_GUESS = "Which one do you think was written from the video? [a/b/no idea] "


def _ask(question: str, allowed: set[str]) -> str:
    while True:
        answer = input(question).strip().lower()
        if answer in allowed:
            return answer
        print(f"  please answer one of: {', '.join(sorted(allowed))}")


def parse_pairs(spec: str | None) -> set[frozenset[str]] | None:
    """"telemetry:video_dense,telemetry:video_sparse" -> {{telemetry, video_dense}, ...}; None = all pairs."""
    if not spec:
        return None
    pairs = set()
    for item in spec.split(","):
        names = [n.strip() for n in item.split(":")]
        if len(names) != 2 or not all(names) or names[0] == names[1]:
            raise SystemExit(f"bad --pairs entry {item!r}: expected two different conditions, like telemetry:video_dense")
        pairs.add(frozenset(names))
    return pairs


def select_items(records: list[dict], wanted: set[frozenset[str]] | None) -> list[tuple[dict, str, str]]:
    items = []
    for rec in records:
        available = [c for c in rec["conditions"] if rec["conditions"][c].get("aar")]
        for left, right in itertools.combinations(sorted(available), 2):
            if wanted is None or frozenset((left, right)) in wanted:
                items.append((rec, left, right))
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("results/run"))
    parser.add_argument("--rater", required=True, help="your name; one file per rater")
    parser.add_argument("--seed", type=int, default=0, help="same seed = same order for every rater")
    parser.add_argument("--pairs", default=None,
                        help="only these condition pairs, comma-separated, e.g. telemetry:video_dense (default: all pairs)")
    args = parser.parse_args()

    records = json.loads((args.run / "results.json").read_text())
    wanted = parse_pairs(args.pairs)
    if wanted:
        known = {c for rec in records for c in rec["conditions"]}
        unknown = sorted({n for pair in wanted for n in pair} - known)
        if unknown:
            raise SystemExit(f"unknown condition(s) in --pairs: {', '.join(unknown)}; this run has {', '.join(sorted(known))}")
    out_dir = args.run / "ratings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.rater}.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else []
    seen = {(row["trial_id"], row["pair"]) for row in done}

    rng = random.Random(args.seed)
    items = select_items(records, wanted)
    rng.shuffle(items)

    for i, (rec, left, right) in enumerate(items, 1):
        pair = f"{left}_vs_{right}"
        if (rec["trial_id"], pair) in seen:
            continue
        order = [left, right]
        rng.shuffle(order)  # which one is shown as A
        print(f"\n{'=' * 72}\n{i}/{len(items)}  episode {rec['trial_id']}  ({rec['layout']}, final score {int(rec['final_score'])})")
        print(f"Watch the episode first: {rec['video']}")
        for tag, condition in zip("AB", order):
            print(f"\n--- Review {tag} ---\n{rec['conditions'][condition]['aar']}")
        print()

        row = {"trial_id": rec["trial_id"], "pair": pair, "shown_as": {"A": order[0], "B": order[1]}, "rater": args.rater}
        for name, question in _QUESTIONS:
            answer = _ask(question, {"a", "b", "tie"})
            row["question"] = name
            row["winner"] = "tie" if answer == "tie" else order[0 if answer == "a" else 1]
            done.append(dict(row))
        guess = _ask(_GUESS, {"a", "b", "no idea"})
        done.append(
            {
                **row,
                "question": "source_guess",
                "winner": "no idea" if guess == "no idea" else order[0 if guess == "a" else 1],
            }
        )
        out_path.write_text(json.dumps(done, indent=2))
        print(f"  saved -> {out_path}")

    print(f"\ndone: {len(done)} answers in {out_path}")


if __name__ == "__main__":
    main()
