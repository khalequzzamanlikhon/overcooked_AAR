"""Checks on which comparisons the rating tool shows.

    python -m pytest tests -q
"""
from __future__ import annotations

import pytest

from rate_aars import parse_pairs, select_items

CONDITIONS = ["telemetry", "video_dense", "video_sparse"]


def _records(n: int) -> list[dict]:
    return [{"trial_id": str(i), "conditions": {c: {"aar": "review"} for c in CONDITIONS}} for i in range(n)]


def test_default_shows_every_pair():
    assert len(select_items(_records(15), parse_pairs(None))) == 45


def test_pairs_limits_the_comparisons():
    items = select_items(_records(15), parse_pairs("telemetry:video_dense"))
    assert len(items) == 15
    assert {(left, right) for _, left, right in items} == {("telemetry", "video_dense")}


def test_pair_order_does_not_matter():
    assert parse_pairs("video_dense:telemetry") == parse_pairs("telemetry:video_dense")


def test_conditions_without_a_review_are_skipped():
    records = _records(2)
    records[0]["conditions"]["video_dense"]["aar"] = ""
    assert len(select_items(records, parse_pairs("telemetry:video_dense"))) == 1


@pytest.mark.parametrize("spec", ["telemetry", "telemetry:telemetry", "telemetry:"])
def test_bad_pairs_are_rejected(spec):
    with pytest.raises(SystemExit):
        parse_pairs(spec)
