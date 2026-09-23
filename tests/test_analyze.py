"""Checks on the chance baselines in analyze.py.

    python -m pytest tests -q
"""
from __future__ import annotations

import pytest

from analyze import chance_baselines


def _event(seconds: float, player: int | None) -> dict:
    return {
        "t": int(seconds * 6.7),
        "seconds": seconds,
        "kind": "delivery",
        "player": player,
        "item": "soup",
        "text": "a soup was delivered",
        "duration": 0.0,
        "extra": {},
    }


def _record(event_player: int | None, claims: list[dict]) -> dict:
    return {
        "events": [_event(10.0, event_player)],
        "conditions": {"video_dense": {"segments": [{"start": 0.0, "end": 60.0, "claims": claims}]}},
    }


def _claim(player: str, status: str = "supported", type_: str = "delivery") -> dict:
    return {"time": 10.0, "player": player, "type": type_, "text": "delivered a soup", "verdict": {"status": status}}


def test_random_time_matches_the_share_of_the_minute_in_tolerance():
    """One delivery at 10 s, 3 s tolerance: a random time hits 6 s of 60."""
    got = chance_baselines([_record(0, [_claim("P1")])], draws=4000)["video_dense"]
    assert got["supported_at_random_time"] == pytest.approx(0.1, abs=0.02)


def test_swapping_the_player_contradicts_a_named_claim():
    got = chance_baselines([_record(0, [_claim("P1")])])["video_dense"]
    assert got["not_contradicted_named"] == 1.0
    assert got["not_contradicted_swapped"] == 0.0


def test_swap_cannot_hurt_a_claim_about_an_unattributed_event():
    got = chance_baselines([_record(None, [_claim("P1")])])["video_dense"]
    assert got["not_contradicted_swapped"] == 1.0


def test_unchecked_and_unnamed_claims_are_left_out():
    claims = [_claim("P1", status="unchecked", type_="strategy"), _claim("BOTH")]
    got = chance_baselines([_record(0, claims)])["video_dense"]
    assert got["not_contradicted_named"] is None
    assert got["supported_at_random_time"] is not None  # "both" still counts for timing
