"""Confidence intervals that respect how the data was sampled.

Claims from the same episode are not independent, so every interval here comes
from resampling whole episodes (10,000 times by default). A rate is a ratio of
sums over the resampled episodes, not a mean of per-episode rates, so an
episode with 40 claims weighs more than one with 4, as it does in the point
estimate.

Differences between two conditions are paired: both are computed on the same
resampled episodes. A Wilcoxon signed-rank test on the per-episode rates is
reported next to each difference.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon

N_BOOT = 10_000
N_BOOT_MEDIAN = 2_000  # medians need the pooled values per resample; slower


def boot_indices(n: int, n_boot: int = N_BOOT, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def ratio(num: np.ndarray, den: np.ndarray) -> float | None:
    d = float(np.sum(den))
    return None if d == 0 else float(np.sum(num)) / d


def ratio_ci(num, den, idx: np.ndarray, level: float = 0.95) -> dict:
    """Point estimate and percentile CI of sum(num)/sum(den) over episodes."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    value = ratio(num, den)
    if value is None:
        return {"value": None, "ci": [None, None]}
    n_s, d_s = num[idx].sum(axis=1), den[idx].sum(axis=1)
    ok = d_s > 0
    draws = n_s[ok] / d_s[ok]
    lo, hi = np.percentile(draws, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return {"value": round(value, 4), "ci": [round(float(lo), 4), round(float(hi), 4)]}


def paired_diff(num_a, den_a, num_b, den_b, idx: np.ndarray, level: float = 0.95) -> dict:
    """(rate A - rate B), CI from the same resampled episodes, plus Wilcoxon."""
    num_a, den_a, num_b, den_b = (np.asarray(x, float) for x in (num_a, den_a, num_b, den_b))
    a, b = ratio(num_a, den_a), ratio(num_b, den_b)
    if a is None or b is None:
        return {"diff": None, "ci": [None, None], "wilcoxon_p": None, "n_episodes": 0}
    da, db = den_a[idx].sum(1), den_b[idx].sum(1)
    ok = (da > 0) & (db > 0)
    draws = num_a[idx].sum(1)[ok] / da[ok] - num_b[idx].sum(1)[ok] / db[ok]
    lo, hi = np.percentile(draws, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    both = (den_a > 0) & (den_b > 0)
    per_a, per_b = num_a[both] / den_a[both], num_b[both] / den_b[both]
    p = None
    if both.sum() >= 5 and np.any(per_a != per_b):
        p = float(wilcoxon(per_a, per_b, zero_method="zsplit").pvalue)
    return {"diff": round(a - b, 4), "ci": [round(float(lo), 4), round(float(hi), 4)],
            "wilcoxon_p": None if p is None else round(p, 5), "n_episodes": int(both.sum())}


def median_ci(per_episode: list[list[float]], n_boot: int = N_BOOT_MEDIAN, seed: int = 0, level: float = 0.95) -> dict:
    """Median (and IQR) of values pooled over episodes, CI by episode resampling."""
    pooled = [v for ep in per_episode for v in ep]
    if not pooled:
        return {"value": None, "iqr": [None, None], "ci": [None, None]}
    idx = boot_indices(len(per_episode), n_boot, seed)
    arrays = [np.asarray(ep, float) for ep in per_episode]
    meds = []
    for row in idx:
        vals = np.concatenate([arrays[i] for i in row])
        if vals.size:
            meds.append(np.median(vals))
    lo, hi = np.percentile(meds, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    q1, q3 = np.percentile(pooled, [25, 75])
    return {"value": round(float(np.median(pooled)), 3), "iqr": [round(float(q1), 3), round(float(q3), 3)],
            "ci": [round(float(lo), 3), round(float(hi), 3)]}


def krippendorff_alpha(units: dict[str, list], level: str = "nominal") -> float | None:
    """Krippendorff's alpha for units -> list of ratings (one per rater who rated it).

    `level` is "nominal" (e.g. which review won) or "interval" (1-5 scores).
    """
    units = {k: [v for v in vals if v is not None] for k, vals in units.items()}
    units = {k: v for k, v in units.items() if len(v) >= 2}
    if not units:
        return None
    values = sorted({v for vals in units.values() for v in vals}, key=str)

    def delta(a, b) -> float:
        if level == "interval":
            return (float(a) - float(b)) ** 2
        return 0.0 if a == b else 1.0

    n_total = sum(len(v) for v in units.values())
    d_obs = 0.0
    for vals in units.values():
        m = len(vals)
        d_obs += sum(delta(a, b) for i, a in enumerate(vals) for j, b in enumerate(vals) if i != j) / (m - 1)
    d_obs /= n_total
    pooled = [v for vals in units.values() for v in vals]
    d_exp = sum(delta(a, b) for i, a in enumerate(pooled) for j, b in enumerate(pooled) if i != j)
    d_exp /= n_total * (n_total - 1)
    if d_exp == 0:
        return 1.0 if len(values) == 1 else None
    return round(1 - d_obs / d_exp, 4)
