"""Checks on the bootstrap and agreement statistics.

    python -m pytest tests -q
"""
from __future__ import annotations

import numpy as np
import pytest

from aar.stats import boot_indices, krippendorff_alpha, paired_diff, ratio_ci


def test_ratio_ci_is_a_ratio_of_sums_and_brackets_it():
    num, den = np.array([1, 9, 5, 5]), np.array([10, 10, 10, 10])
    got = ratio_ci(num, den, boot_indices(4, 2000))
    assert got["value"] == pytest.approx(0.5)
    assert got["ci"][0] <= 0.5 <= got["ci"][1]


def test_identical_conditions_differ_by_zero():
    num, den = np.array([3, 4, 5, 6, 7, 2]), np.array([10] * 6)
    got = paired_diff(num, den, num, den, boot_indices(6, 1000))
    assert got["diff"] == 0 and got["ci"] == [0, 0] and got["wilcoxon_p"] is None


def test_krippendorff_alpha():
    perfect = {"u1": ["a", "a"], "u2": ["b", "b"], "u3": ["a", "a"]}
    assert krippendorff_alpha(perfect) == 1.0
    # the textbook example (Krippendorff 2011, nominal, 4 coders, missing data) has alpha = 0.743
    data = {
        1: [1, 1, 1], 2: [2, 2, 3, 2], 3: [3, 3, 3, 3], 4: [3, 3, 3, 3], 5: [2, 2, 2, 2], 6: [1, 2, 3, 4],
        7: [4, 4, 4, 4], 8: [1, 1, 2, 1], 9: [2, 2, 2, 2], 10: [5, 5, 5], 11: [1, 1], 12: [3],
    }
    assert krippendorff_alpha(data) == pytest.approx(0.743, abs=0.001)
