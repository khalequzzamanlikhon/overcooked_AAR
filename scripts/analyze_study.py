"""Put the study-v2 runs side by side: model x condition, model differences, variance.

    python scripts/analyze_study.py --root results/v2

Reads <root>/<model>/metrics_v2.json (run analyze.py on each run first),
<root>/<model>/results.json for the paired model comparisons, and
<root>/variance/<model>_seed<k>/metrics_v2.json if the variance repeat ran.
Writes <root>/SUMMARY.md and <root>/summary.json.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aar import stats  # noqa: E402
from aar.config import MODELS  # noqa: E402
from aar.metrics import episode_counts  # noqa: E402
from aar.report_v2 import ORDER, _p, _series  # noqa: E402

# (A, B) model pairs: A - B on the same episodes
MODEL_PAIRS = [("qwen25vl7b_bf16", "qwen25vl7b_4bit"), ("qwen3vl8b_bf16", "qwen25vl7b_bf16")]
PAIR_CONDITIONS = ["telemetry", "video_dense", "video_sparse", "video_log", "state_text", "blind"]


def _load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("results/v2"))
    args = parser.parse_args()
    root = args.root
    lines = ["# Study v2: summary across models", ""]
    summary: dict = {"models": {}, "model_pairs": {}, "variance": {}}

    for suffix, heading in [("_pilot15", "The pilot's 15 episodes"), ("", "All episodes")]:
        rows = []
        for tag in MODELS:
            m = _load(root / tag / f"metrics_v2{suffix}.json")
            if m is None and suffix == "_pilot15":
                m = _load(root / tag / "metrics_v2.json")  # a run of only the pilot's episodes
                if m and m["episodes"] != 15:
                    m = None
            if m is None:
                continue
            summary["models"].setdefault(tag, {})[suffix or "all"] = m
            for c in ORDER:
                cm = m["conditions"].get(c)
                if not cm or "precision" not in cm:
                    continue
                te = cm["time_error_s"]["value"]
                rows.append(f"| {tag} | {c} | {m['episodes']} | {_p(cm['precision'])} | {_p(cm['recall'])} | "
                            f"{_p(cm['by_type']['delivery']['recall'])} | {_p(cm['actor_accuracy'])} | "
                            f"{'-' if te is None else f'{te:.1f}'} | {cm['above_chance_area']:.3f} | "
                            f"{_p(cm['aar_check'].get('timed_error_rate')) if cm.get('aar_check') else '-'} |")
        if rows:
            lines += [f"## {heading}", "",
                      "| model | condition | episodes | precision | recall | delivery recall | actor accuracy "
                      "| median time error, s | above-chance area | review statements wrong |",
                      "|---|---|---|---|---|---|---|---|---|---|", *rows, ""]

    # paired model comparisons on the episodes both models finished
    lines += ["## Model differences on the same episodes (A - B)", "",
              "| A - B | condition | episodes | precision | recall | delivery recall |", "|---|---|---|---|---|---|"]
    for a, b in MODEL_PAIRS:
        ra, rb = _load(root / a / "results.json"), _load(root / b / "results.json")
        ca, cb = _load(root / a / "config.json") or {}, _load(root / b / "config.json") or {}
        if not ra or not rb:
            continue
        ra, rb = {r["trial_id"]: r for r in ra}, {r["trial_id"]: r for r in rb}
        for c in PAIR_CONDITIONS:
            common = sorted(t for t in set(ra) & set(rb)
                            if ra[t]["conditions"].get(c, {}).get("segments") and rb[t]["conditions"].get(c, {}).get("segments"))
            if len(common) < 2:
                continue
            ea = [episode_counts(ra[t], c, ca.get("claim_cap", 20), draws=0) for t in common]
            eb = [episode_counts(rb[t], c, cb.get("claim_cap", 20), draws=0) for t in common]
            idx = stats.boot_indices(len(common))
            cells, entry = [], {}
            for metric, (num, den) in {"precision": ("supported", "checkable"), "recall": ("events_recalled", "events"),
                                       "delivery_recall": ("recall_delivery_hit", "recall_delivery_events")}.items():
                d = stats.paired_diff(_series(ea, num), _series(ea, den), _series(eb, num), _series(eb, den), idx)
                entry[metric] = d
                p = "" if d["wilcoxon_p"] is None else f", p={d['wilcoxon_p']:.3g}"
                cells.append("-" if d["diff"] is None else
                             f"{d['diff'] * 100:+.0f} [{d['ci'][0] * 100:+.0f}, {d['ci'][1] * 100:+.0f}]{p}")
            summary["model_pairs"][f"{a} - {b} | {c}"] = entry
            lines.append(f"| {a} - {b} | {c} | {len(common)} | " + " | ".join(cells) + " |")
    lines.append("")

    # sampled-decoding repeat
    var_root = root / "variance"
    if var_root.exists():
        lines += ["## Sampled decoding, 3 seeds (the pilot's 15 episodes)", "",
                  "| model | condition | greedy precision | sampled precision, mean ± sd | sampled recall, mean ± sd |",
                  "|---|---|---|---|---|"]
        for tag in MODELS:
            runs = [_load(p / "metrics_v2.json") for p in sorted(var_root.glob(f"{tag}_seed*"))]
            runs = [r for r in runs if r]
            greedy = summary["models"].get(tag, {}).get("_pilot15") or summary["models"].get(tag, {}).get("all")
            if not runs:
                continue
            for c in sorted({c for r in runs for c in r["conditions"]}, key=lambda c: ORDER.index(c) if c in ORDER else 99):
                prec = [r["conditions"][c]["precision"]["value"] for r in runs if c in r["conditions"]]
                rec = [r["conditions"][c]["recall"]["value"] for r in runs if c in r["conditions"]]
                prec, rec = [p for p in prec if p is not None], [r for r in rec if r is not None]
                if not prec:
                    continue
                g = greedy["conditions"].get(c, {}).get("precision") if greedy else None
                sd = lambda v: statistics.stdev(v) if len(v) > 1 else 0.0  # noqa: E731
                summary["variance"][f"{tag}|{c}"] = {"precision": prec, "recall": rec}
                lines.append(f"| {tag} | {c} | {_p(g)} | {statistics.mean(prec) * 100:.1f} ± {sd(prec) * 100:.1f} | "
                             f"{statistics.mean(rec) * 100:.1f} ± {sd(rec) * 100:.1f} |")
        lines.append("")

    probe = root / "probe" / "probe_summary.md"
    if probe.exists():
        lines += ["## Perception probe", "", f"See [{probe.relative_to(root)}]({probe.relative_to(root)}) and "
                  "`probe/probe_ladder.png`.", ""]
    (root / "SUMMARY.md").write_text("\n".join(lines))
    (root / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
