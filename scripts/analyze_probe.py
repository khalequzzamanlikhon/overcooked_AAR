"""Score the perception probe: accuracy per question type, form and model.

    python scripts/analyze_probe.py --probe results/v2/probe

Reads <probe>/<model>/<variant>.jsonl, writes <probe>/probe_summary.{md,json}
and <probe>/probe_ladder.png. CIs resample episodes, since items from one
episode share a layout and a pair of players.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aar import stats  # noqa: E402
from aar.probe import QTYPES, VARIANTS, chance  # noqa: E402

COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # reference categorical slots 1-3, fixed order by model
GRAY = "#8a8984"


def _acc(rows: list[dict]) -> dict:
    by_trial: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        by_trial[r["trial_id"]][0] += r["correct"]
        by_trial[r["trial_id"]][1] += 1
    num = np.array([v[0] for v in by_trial.values()])
    den = np.array([v[1] for v in by_trial.values()])
    out = stats.ratio_ci(num, den, stats.boot_indices(len(num), 2000))
    out["n"] = len(rows)
    out["parsed"] = round(sum(r.get("parsed", False) for r in rows) / len(rows), 3)
    errs = [r["abs_error"] for r in rows if r.get("abs_error") is not None]
    if errs:
        out["median_abs_error_s"] = round(float(np.median(errs)), 2)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, default=Path("results/v2/probe"))
    parser.add_argument("--items", type=Path, default=Path("probes/probe_v1.jsonl"))
    args = parser.parse_args()

    items = [json.loads(line) for line in args.items.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_type = defaultdict(list)
    for it in items:
        by_type[it["qtype"]].append(it)
    chances = {q: chance(v) for q, v in by_type.items()}

    models = sorted(p for p in args.probe.iterdir() if p.is_dir() and (p / "config.json").exists())
    result: dict = {"chance": chances, "models": {}}
    for mdir in models:
        per_variant = {}
        for variant in VARIANTS:
            path = mdir / f"{variant}.jsonl"
            if not path.exists():
                continue
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            grouped = defaultdict(list)
            for r in rows:
                grouped[r["qtype"]].append(r)
            per_variant[variant] = {q: _acc(rs) for q, rs in grouped.items()}
        result["models"][mdir.name] = per_variant
    (args.probe / "probe_summary.json").write_text(json.dumps(result, indent=2))

    def cell(m):
        if not m or m.get("value") is None:
            return "-"
        s = f"{m['value'] * 100:.0f}% [{m['ci'][0] * 100:.0f}, {m['ci'][1] * 100:.0f}]"
        if "median_abs_error_s" in m:
            s += f", median error {m['median_abs_error_s']:.1f} s"
        return s

    lines = ["# Perception probe", "",
             f"{len(items)} items from all 76 episodes. Brackets: 95% CIs, resampling episodes.", "",
             "## Video vs. the same information as text", ""]
    header = "| question | chance (uniform / majority) | " + " | ".join(
        f"{m} video | {m} text" for m in result["models"]) + " |"
    lines += [header, "|---|---|" + "---|---|" * len(result["models"])]
    for q in QTYPES:
        ch = chances.get(q, {})
        uni = "-" if "uniform" not in ch else f"{ch['uniform'] * 100:.0f}%"
        row = f"| {q} | {uni} / {ch.get('majority', 0) * 100:.0f}% | "
        row += " | ".join(f"{cell(v.get('video_main', {}).get(q))} | {cell(v.get('text', {}).get(q))}"
                          for v in result["models"].values())
        lines.append(row + " |")
    for title, variants in [("Frames per second (clip questions)", ["video_fps0.33", "video_fps1", "video_main", "video_fps4"]),
                            ("What is on screen above the grid", ["video_main", "video_hud_clock", "video_hud_none"])]:
        lines += ["", f"## {title}", ""]
        for model, v in result["models"].items():
            qs = sorted({q for var in variants for q in v.get(var, {})}, key=QTYPES.index)
            if not qs:
                continue
            lines += [f"**{model}**", "", "| variant | " + " | ".join(qs) + " |", "|---|" + "---|" * len(qs)]
            for var in variants:
                if var in v:
                    lines.append(f"| {var} | " + " | ".join(cell(v[var].get(q)) for q in qs) + " |")
            lines.append("")
    lines += ["`video_main` is 2 fps with the clock and score strip; `video_hud_clock` drops the score, "
              "`video_hud_none` drops the strip. For L3_localize, *accuracy* is within 3 s."]
    (args.probe / "probe_summary.md").write_text("\n".join(lines) + "\n")

    # the ladder: accuracy by question type, video and text side by side, one line per model
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6})
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    x = np.arange(len(QTYPES))
    for ax, variant, title in [(axes[0], "video_main", "video (2 fps)"), (axes[1], "text", "same information as text")]:
        for k, (model, v) in enumerate(result["models"].items()):
            ys = [v.get(variant, {}).get(q, {}).get("value") for q in QTYPES]
            xs = [xi for xi, y in zip(x, ys) if y is not None]
            ax.plot(xs, [y for y in ys if y is not None], color=COLORS[k % 3], linewidth=2, marker="o",
                    markersize=5, label=model)
        ch = [chances.get(q, {}).get("uniform", chances.get(q, {}).get("majority")) for q in QTYPES]
        ax.scatter(x, [c if c is not None else np.nan for c in ch], marker="_", s=160, color=GRAY, label="chance")
        ax.set_xticks(x, [q.replace("_", " ", 1) for q in QTYPES], rotation=45, ha="right")
        ax.set_title(title)
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("accuracy")
    axes[1].legend(frameon=False, loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(args.probe / "probe_ladder.png", dpi=160)
    print(f"-> {args.probe / 'probe_summary.md'}")


if __name__ == "__main__":
    main()
