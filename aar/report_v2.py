"""Study-v2 tables for one run: every metric with an episode-bootstrap 95% CI.

Called from analyze.py; writes metrics_v2.json, metrics_v2.md and figures/.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import stats
from .aar_check import check_review
from .metrics import BEHAVIOR_TYPES, RECALL_KINDS, TOLERANCES, entropy_bits, episode_counts

# condition pairs worth a paired test, when both are present: (A, B) reports A - B
PAIRS = [
    ("telemetry", "video_dense"), ("telemetry", "video_sparse"), ("telemetry", "blind"),
    ("video_dense", "blind"), ("video_sparse", "blind"), ("video_dense", "video_sparse"),
    ("video_log", "telemetry"), ("video_log", "video_dense"), ("state_text", "telemetry"),
    ("state_text", "video_dense"),
]
ORDER = ["blind", "telemetry", "video_dense", "video_sparse", "video_log", "state_text", "oracle"]
# series colours (reference categorical palette, fixed order) and a neutral for baselines
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"


def _conditions(records: list[dict]) -> list[str]:
    present = {c for r in records for c in r["conditions"]}
    return [c for c in ORDER if c in present] + sorted(present - set(ORDER))


def _series(per_ep: list[dict], key: str) -> np.ndarray:
    return np.array([ep["counts"].get(key, 0.0) for ep in per_ep], float)


def _r(per_ep, num, den, idx):
    return stats.ratio_ci(_series(per_ep, num), _series(per_ep, den), idx)


def condition_summary(per_ep: list[dict], idx: np.ndarray, with_behaviors: bool) -> dict:
    out: dict = {
        "episodes": len(per_ep),
        "claims": int(_series(per_ep, "claims").sum()),
        "checkable": int(_series(per_ep, "checkable").sum()),
        "precision": _r(per_ep, "supported", "checkable", idx),
        "precision_named": _r(per_ep, "named_supported", "named_checkable", idx),
        "precision_both_unclear": _r(per_ep, "unnamed_supported", "unnamed_checkable", idx),
        "duplicate": _r(per_ep, "duplicate", "checkable", idx),
        "wrong_time": _r(per_ep, "wrong_time", "checkable", idx),
        "contradicted": _r(per_ep, "contradicted", "checkable", idx),
        "recall": _r(per_ep, "events_recalled", "events", idx),
        "recall_ceiling": _r(per_ep, "events_ceiling", "events", idx),
        "recall_vs_ceiling": _r(per_ep, "events_recalled", "events_ceiling", idx),
        "actor_accuracy": _r(per_ep, "actor_correct", "actor_checked", idx),
        "swap_not_contradicted": _r(per_ep, "swap_named_ok", "swap_named", idx),
        "swap_not_contradicted_swapped": _r(per_ep, "swap_swapped_ok", "swap_named", idx),
        "delivery_mae": _r(per_ep, "delivery_abs_err", "delivery_answers", idx),
        "delivery_signed_error": _r(per_ep, "delivery_signed_err", "delivery_answers", idx),
        "delivery_exact": _r(per_ep, "delivery_exact", "delivery_answers", idx),
        "delivery_says_one": _r(per_ep, "delivery_says_one", "delivery_answers", idx),
        "round5_timestamps": _r(per_ep, "round5", "timed", idx),
        "minutes_repeated": _r(per_ep, "minutes_repeated", "minutes", idx),
        "strict_alternation": _r(per_ep, "alternating", "alternation_eligible", idx),
        "unsupported_before_window": _r(per_ep, "before_window", "unsupported", idx),
        "unsupported_rescued_by_offset": _r(per_ep, "offset_rescued", "unsupported", idx),
        "pickup_precision_incl_fill": _r(per_ep, "pickup_fill_supported", "pickup_fill_checkable", idx),
        "parse_failures": int(_series(per_ep, "parse_failures").sum()),
        "time_error_s": stats.median_ci([ep["lists"].get("time_errors", []) for ep in per_ep]),
    }
    answers = [claimed for ep in per_ep for _, claimed in ep["lists"].get("delivery_pairs", [])]
    out["delivery_answer_entropy_bits"] = None if not answers else round(entropy_bits(answers), 3)
    # actor chance: independent labels with the same marginals
    n = _series(per_ep, "actor_checked").sum()
    if n:
        pc, pe = _series(per_ep, "actor_claim_p1").sum() / n, _series(per_ep, "actor_event_p1").sum() / n
        out["actor_chance"] = round(pc * pe + (1 - pc) * (1 - pe), 4)
    # per type
    by_type = {}
    for ctype in RECALL_KINDS:
        if ctype in BEHAVIOR_TYPES and not with_behaviors:
            continue
        p = _r(per_ep, f"type_{ctype}_supported", f"type_{ctype}_checkable", idx)
        r = _r(per_ep, f"recall_{ctype}_hit", f"recall_{ctype}_events", idx)
        f1 = None
        if p["value"] and r["value"]:
            f1 = round(2 * p["value"] * r["value"] / (p["value"] + r["value"]), 4)
        by_type[ctype] = {"claims": int(_series(per_ep, f"type_{ctype}_checkable").sum()), "precision": p,
                          "events": int(_series(per_ep, f"recall_{ctype}_events").sum()), "recall": r, "f1": f1}
    out["by_type"] = by_type
    # tolerance curve with its random-time baseline
    curve, area = [], 0.0
    for k, tol in enumerate(TOLERANCES):
        s = _r(per_ep, f"tol_{tol}_supported", f"tol_{tol}_checkable", idx)
        b = _r(per_ep, f"tol_{tol}_random_supported", f"tol_{tol}_checkable", idx)
        curve.append({"tol": tol, "supported": s, "random": b})
        if k and s["value"] is not None and curve[k - 1]["supported"]["value"] is not None:
            width = tol - TOLERANCES[k - 1]
            above = (s["value"] - b["value"] + curve[k - 1]["supported"]["value"] - curve[k - 1]["random"]["value"]) / 2
            area += width * above
    out["tolerance_curve"] = curve
    out["above_chance_area"] = round(area / (TOLERANCES[-1] - TOLERANCES[0]), 4)
    return out


def aar_summary(records: list[dict], condition: str, idx_for) -> dict:
    per = []
    for rec in records:
        block = rec["conditions"].get(condition)
        if not block or not block.get("aar"):
            continue
        events = rec["events"] + (rec.get("behaviors") or {}).get("1.0", [])
        per.append(check_review(block["aar"], sorted(events, key=lambda e: e["seconds"])))
    if not per:
        return {}
    idx = idx_for(len(per))
    err = np.array([p["timed_errors"] for p in per], float)
    tot = np.array([p["timed_statements"] for p in per], float)
    has_count_err = np.array([p["count_errors"] > 0 for p in per], float)
    ones = np.ones(len(per))
    return {
        "reviews": len(per),
        "timed_statements": int(tot.sum()),
        "timed_error_rate": stats.ratio_ci(err, tot, idx),
        "reviews_with_count_error": stats.ratio_ci(has_count_err, ones, idx),
        "count_statements": int(sum(p["count_statements"] for p in per)),
        "examples": [e for p in per for e in p["errors"]][:5],
    }


def analyze_run(records: list[dict], cap: int, draws: int = 10) -> dict:
    conditions = _conditions(records)
    with_behaviors = any(r.get("behaviors") for r in records)
    per_cond: dict[str, dict[str, dict]] = defaultdict(dict)
    for rec in records:
        for c in conditions:
            block = rec["conditions"].get(c)
            if block and block.get("segments"):
                per_cond[c][rec["trial_id"]] = episode_counts(rec, c, cap, draws=draws)

    def idx_for(n: int):
        return stats.boot_indices(n)

    summary = {}
    for c in conditions:
        eps = list(per_cond[c].values())
        entry = condition_summary(eps, idx_for(len(eps)), with_behaviors) if eps else {}
        # behaviour thresholds at 0.5x and 1.5x: does the behaviour precision/recall hold up?
        if eps and with_behaviors:
            sens = {}
            for scale in ("0.5", "1.5"):
                alt = [episode_counts(rec, c, cap, draws=0, behavior_scale=scale) for rec in records
                       if rec["conditions"].get(c, {}).get("segments")]
                sens[scale] = {
                    b: {"precision": _r(alt, f"type_{b}_supported", f"type_{b}_checkable", idx_for(len(alt)))["value"],
                        "recall": _r(alt, f"recall_{b}_hit", f"recall_{b}_events", idx_for(len(alt)))["value"]}
                    for b in BEHAVIOR_TYPES
                }
            entry["behavior_sensitivity"] = sens
        entry["aar_check"] = aar_summary(records, c, idx_for)
        summary[c] = entry

    paired = {}
    for a, b in PAIRS:
        if a not in per_cond or b not in per_cond:
            continue
        common = sorted(set(per_cond[a]) & set(per_cond[b]))
        if len(common) < 2:
            continue
        ea, eb = [per_cond[a][t] for t in common], [per_cond[b][t] for t in common]
        idx = idx_for(len(common))
        paired[f"{a} - {b}"] = {
            metric: stats.paired_diff(_series(ea, num), _series(ea, den), _series(eb, num), _series(eb, den), idx)
            for metric, (num, den) in {
                "precision": ("supported", "checkable"),
                "recall": ("events_recalled", "events"),
                "delivery_recall": ("recall_delivery_hit", "recall_delivery_events"),
                "actor_accuracy": ("actor_correct", "actor_checked"),
            }.items()
        }
    return {"conditions": summary, "paired": paired, "claim_cap": cap, "episodes": len(records),
            "tolerances": list(TOLERANCES)}


# ---------------------------------------------------------------- markdown


def _p(m: dict | None) -> str:
    if not m or m.get("value") is None:
        return "-"
    lo, hi = m["ci"]
    return f"{m['value'] * 100:.0f}% [{lo * 100:.0f}, {hi * 100:.0f}]"


def _n(m: dict | None, digits: int = 2) -> str:
    if not m or m.get("value") is None:
        return "-"
    lo, hi = m["ci"]
    return f"{m['value']:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


def to_markdown(result: dict, title: str) -> str:
    cond = result["conditions"]
    lines = [f"# {title}", "",
             f"Episodes: {result['episodes']}. Claim cap per minute: {result['claim_cap']}. "
             "Brackets are 95% CIs from resampling episodes (10,000 draws).", "",
             "## Claims", "",
             "| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall "
             "| actor accuracy (chance) | median time error, s |",
             "|---|---|---|---|---|---|---|---|---|"]
    for c, m in cond.items():
        if "precision" not in m:
            continue
        te = m["time_error_s"]
        tes = "-" if te["value"] is None else f"{te['value']:.1f} [{te['ci'][0]:.1f}, {te['ci'][1]:.1f}]"
        chance = m.get("actor_chance")
        chance_s = "-" if chance is None else f"{chance * 100:.0f}%"
        lines.append(
            f"| {c} | {m['claims']} | {_p(m['precision'])} | {_p(m['precision_named'])} | {_p(m['recall'])} | "
            f"{_p(m['recall_vs_ceiling'])} | {_p(m['by_type']['delivery']['recall'])} | "
            f"{_p(m['actor_accuracy'])} ({chance_s}) | {tes} |"
        )
    lines += ["", "*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. "
              "*recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.",
              "", "## Against chance", "",
              "| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |",
              "|---|---|---|---|---|---|"]
    for c, m in cond.items():
        if "precision" not in m:
            continue
        tol3 = next(p for p in m["tolerance_curve"] if p["tol"] == 3.0)
        lines.append(f"| {c} | {_p(tol3['supported'])} | {_p(tol3['random'])} | {m['above_chance_area']:.3f} | "
                     f"{_p(m['swap_not_contradicted'])} | {_p(m['swap_not_contradicted_swapped'])} |")
    lines += ["", "*above-chance area*: mean gap between the supported rate and its random-time baseline over "
              "tolerances 0.5-10 s. Zero means the timestamps carry no information.",
              "", "## Where claims go wrong", "",
              "| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish "
              "| before the window | rescued by +start |", "|---|---|---|---|---|---|---|---|"]
    for c, m in cond.items():
        if "precision" not in m:
            continue
        lines.append(f"| {c} | {_p(m['duplicate'])} | {_p(m['wrong_time'])} | {_p(m['contradicted'])} | "
                     f"{_p(m['precision_both_unclear'])} | {_p(m['pickup_precision_incl_fill'])} | "
                     f"{_p(m['unsupported_before_window'])} | {_p(m['unsupported_rescued_by_offset'])} |")
    lines += ["", "*rescued by +start*: unsupported claims that would be supported if their time were read as "
              "seconds since the clip started.", "", "## Counting and output collapse", "",
              "| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid "
              "| repeated minutes | strict P1/P2 alternation | parse failures |", "|---|---|---|---|---|---|---|---|---|---|"]
    for c, m in cond.items():
        if "precision" not in m:
            continue
        lines.append(f"| {c} | {_n(m['delivery_mae'])} | {_n(m['delivery_signed_error'])} | {_p(m['delivery_exact'])} | "
                     f"{_p(m['delivery_says_one'])} | {m['delivery_answer_entropy_bits']} | {_p(m['round5_timestamps'])} | "
                     f"{_p(m['minutes_repeated'])} | {_p(m['strict_alternation'])} | {m['parse_failures']} |")
    types = [t for t in RECALL_KINDS if any(t in m.get("by_type", {}) for m in cond.values())]
    lines += ["", "## By claim type (precision / recall / F1)", "",
              "| condition | " + " | ".join(types) + " |", "|---|" + "---|" * len(types)]
    for c, m in cond.items():
        if "by_type" not in m:
            continue
        cells = []
        for t in types:
            bt = m["by_type"].get(t)
            if not bt:
                cells.append("-")
                continue
            vals = [bt["precision"]["value"], bt["recall"]["value"], bt["f1"]]
            p, r, f1 = ("-" if v is None else f"{v * 100:.0f}" for v in vals)
            cells.append(f"{p} / {r} / {f1} (n={bt['claims']})")
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    if any("behavior_sensitivity" in m for m in cond.values()):
        lines += ["", "Behaviour thresholds at 0.5x / 1.5x (precision / recall):", ""]
        for c, m in cond.items():
            sens = m.get("behavior_sensitivity")
            if sens:
                parts = []
                for b in BEHAVIOR_TYPES:
                    vals = []
                    for s in ("0.5", "1.5"):
                        p, r = sens[s][b]["precision"], sens[s][b]["recall"]
                        vals.append(f"{'-' if p is None else f'{p * 100:.0f}'}/{'-' if r is None else f'{r * 100:.0f}'}")
                    parts.append(f"{b} {' vs '.join(vals)}")
                lines.append(f"- {c}: " + "; ".join(parts))
    lines += ["", "## The written reviews", "",
              "| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |",
              "|---|---|---|---|---|"]
    for c, m in cond.items():
        a = m.get("aar_check")
        if a:
            lines.append(f"| {c} | {a['reviews']} | {a['timed_statements']} | {_p(a['timed_error_rate'])} | "
                         f"{_p(a['reviews_with_count_error'])} |")
    if result["paired"]:
        lines += ["", "## Paired differences (A - B, same episodes)", "",
                  "| A - B | precision | recall | delivery recall | actor accuracy |", "|---|---|---|---|---|"]
        for pair, ms in result["paired"].items():
            cells = []
            for metric in ("precision", "recall", "delivery_recall", "actor_accuracy"):
                d = ms[metric]
                if d["diff"] is None:
                    cells.append("-")
                else:
                    p = "" if d["wilcoxon_p"] is None else f", p={d['wilcoxon_p']:.3g}"
                    cells.append(f"{d['diff'] * 100:+.0f} [{d['ci'][0] * 100:+.0f}, {d['ci'][1] * 100:+.0f}]{p}")
            lines.append(f"| {pair} | " + " | ".join(cells) + " |")
        lines += ["", "Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- figures


def figures(result: dict, records: list[dict], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    cond = {c: m for c, m in result["conditions"].items() if "tolerance_curve" in m}
    if not cond:
        return
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6})
    n = len(cond)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols

    # tolerance curves: one panel per condition, the random-time baseline in gray
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.6 * rows), sharex=True, sharey=True, squeeze=False)
    for ax, (c, m) in zip(axes.flat, cond.items()):
        tol = [p["tol"] for p in m["tolerance_curve"]]
        s = [p["supported"]["value"] or 0 for p in m["tolerance_curve"]]
        lo = [p["supported"]["ci"][0] or 0 for p in m["tolerance_curve"]]
        hi = [p["supported"]["ci"][1] or 0 for p in m["tolerance_curve"]]
        r = [p["random"]["value"] or 0 for p in m["tolerance_curve"]]
        ax.fill_between(tol, lo, hi, color=BLUE, alpha=0.15, linewidth=0)
        ax.plot(tol, s, color=BLUE, linewidth=2, marker="o", markersize=4, label="claimed time")
        ax.plot(tol, r, color=GRAY, linewidth=2, linestyle="--", label="random time")
        ax.set_title(c)
        ax.set_ylim(0, 1)
    for ax in axes.flat[n:]:
        ax.axis("off")
    for ax in axes[-1]:
        ax.set_xlabel("tolerance, s")
    for ax in axes[:, 0]:
        ax.set_ylabel("supported")
    axes.flat[0].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_dir / "tolerance_curves.png", dpi=160)
    plt.close(fig)

    # claimed vs true deliveries per minute
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.8 * rows), sharex=True, sharey=True, squeeze=False)
    top = 1
    for ax, c in zip(axes.flat, cond):
        pts = [(s["deliveries_true"], s["deliveries_claimed"]) for rec in records
               for s in rec["conditions"].get(c, {}).get("segments", []) if s.get("deliveries_claimed") is not None]
        if pts:
            t, k = zip(*pts)
            jitter = np.random.default_rng(0).uniform(-0.15, 0.15, len(t))
            ax.scatter(np.array(t) + jitter, np.array(k) - jitter, s=14, color=BLUE, alpha=0.6, linewidths=0)
            top = max(top, max(t), max(k))
        ax.set_title(c)
    for ax in axes.flat[:n]:
        ax.plot([0, top], [0, top], color=GRAY, linewidth=1, linestyle="--")
    for ax in axes.flat[n:]:
        ax.axis("off")
    for ax in axes[-1]:
        ax.set_xlabel("true deliveries in the minute")
    for ax in axes[:, 0]:
        ax.set_ylabel("claimed")
    fig.tight_layout()
    fig.savefig(out_dir / "delivery_counts.png", dpi=160)
    plt.close(fig)


def write(records: list[dict], run_dir: Path, cap: int, suffix: str = "", title: str = "Study v2 metrics") -> dict:
    result = analyze_run(records, cap)
    (run_dir / f"metrics_v2{suffix}.json").write_text(json.dumps(result, indent=2))
    (run_dir / f"metrics_v2{suffix}.md").write_text(to_markdown(result, title))
    figures(result, records, run_dir / f"figures{suffix}")
    return result
