"""Blind rating harness for the generated AARs.

Shows AARs one at a time with the source hidden and shuffled, so you don't
unconsciously favour the telemetry version because you know which is which.
Writes ratings to ratings.json for analysis.

    python rate_aars.py --results out/results.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

_CRITERIA = {
    "accuracy": "Does it describe what actually happened? (1-5)",
    "specificity": "Is the advice concrete rather than generic? (1-5)",
    "usefulness": "Would this help the team improve? (1-5)",
}


def _prompt_score(label: str, question: str) -> int:
    while True:
        raw = input(f"  {label} - {question} ")
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("  enter 1-5")


def main(results_path: Path, out_path: Path) -> None:
    records = json.loads(results_path.read_text())
    items = []
    for rec in records:
        for source in ("aar_telemetry", "aar_video"):
            if rec.get(source):
                items.append({"trial_id": rec["trial_id"], "source": source, "text": rec[source],
                              "final_score": rec["final_score"], "video": rec.get("video")})
    random.shuffle(items)

    ratings = []
    for i, item in enumerate(items, 1):
        print(f"\n{'=' * 70}\nAAR {i}/{len(items)}  (trial {item['trial_id']}, final score {int(item['final_score'])})")
        print(f"Watch first: {item['video']}")
        print(f"{'-' * 70}\n{item['text']}\n{'-' * 70}")
        scores = {k: _prompt_score(k, q) for k, q in _CRITERIA.items()}
        notes = input("  notes (optional): ")
        ratings.append({**{k: v for k, v in item.items() if k != "text"}, **scores, "notes": notes})
        out_path.write_text(json.dumps(ratings, indent=2))  # save as you go

    by_source: dict[str, list[dict]] = {}
    for r in ratings:
        by_source.setdefault(r["source"], []).append(r)
    print(f"\n{'=' * 70}")
    for source, rs in by_source.items():
        means = {c: sum(r[c] for r in rs) / len(rs) for c in _CRITERIA}
        print(f"{source}: " + "  ".join(f"{c}={m:.2f}" for c, m in means.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("out/results.json"))
    parser.add_argument("--out", type=Path, default=Path("out/ratings.json"))
    args = parser.parse_args()
    main(args.results, args.out)
