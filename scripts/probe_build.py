"""Build the perception-probe items from all 76 episodes (fixed seed).

    python scripts/probe_build.py --out probes/probe_v1.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aar.probe import build_items  # noqa: E402
from run_pipeline import select_episodes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("probes/probe_v1.jsonl"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-frame", type=int, default=150, help="items per single-frame question type")
    parser.add_argument("--n-clip", type=int, default=120, help="items per clip question type")
    args = parser.parse_args()

    trials = [(t, split) for t, split, _ in select_episodes("all")]
    items = build_items(trials, seed=args.seed, n_frame=args.n_frame, n_clip=args.n_clip)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
    print(f"{len(items)} items -> {args.out}")
    for qtype, n in Counter(i["qtype"] for i in items).items():
        golds = Counter(str(i["gold"]) for i in items if i["qtype"] == qtype)
        print(f"  {qtype:14s} {n:4d}  answers: {dict(golds.most_common(5))}")


if __name__ == "__main__":
    main()
