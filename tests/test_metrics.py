"""Checks on the study-v2 scorer (aar/metrics.py), on hand-built minutes.

    python -m pytest tests -q
"""
from __future__ import annotations

import pytest

from aar.metrics import episode_counts, gap, match_segment


def ev(seconds, kind="delivery", player=0, item="soup", duration=0.0, **extra):
    return {"t": int(seconds * 6.7), "seconds": seconds, "kind": kind, "player": player, "item": item,
            "text": "", "duration": duration, "extra": extra}


def cl(time, type_="delivery", player="P1", text="delivered a soup"):
    return {"time": time, "type": type_, "player": player, "text": text}


def statuses(claims, events, **kw):
    return [v["status"] for v in match_segment(claims, events, **kw)]


def test_two_claims_cannot_share_one_event():
    """The pilot's checker let both claims be supported by the one delivery."""
    assert sorted(statuses([cl(44), cl(46)], [ev(45)])) == ["duplicate", "supported"]


def test_matching_prefers_the_assignment_that_supports_the_most_claims():
    # greedy nearest-first would give the 45 s event to the 44 s claim and strand the 47.5 s one
    got = statuses([cl(44.9), cl(47.5)], [ev(45), ev(42)])
    assert got == ["supported", "supported"]


def test_statuses():
    events = [ev(10, player=0)]
    assert statuses([cl(30)], events) == ["wrong_time"]
    assert statuses([cl(10, player="P2")], events) == ["contradicted"]
    assert statuses([cl(10, type_="strategy")], events) == ["unchecked"]
    assert statuses([cl(None)], events) == ["unchecked"]


def test_both_and_unclear_match_either_player():
    assert statuses([cl(10, player="BOTH")], [ev(10, player=1)]) == ["supported"]


def test_an_item_that_does_not_fit_contradicts():
    assert statuses([cl(10, text="delivered an onion")], [ev(10)]) == ["contradicted"]


def test_pickup_is_not_backed_by_filling_a_dish():
    events = [ev(10, kind="fill_dish")]
    assert statuses([cl(10, type_="pickup", text="picked up soup")], events) == ["contradicted"]


def test_a_stretch_counts_from_start_to_end():
    idle = ev(10, kind="idle", item=None, duration=8.0)
    assert gap(idle, 14) == 0
    assert gap(idle, 20) == pytest.approx(2.0)
    assert statuses([cl(16, type_="idle", text="stood still")], [idle]) == ["supported"]


def test_a_handoff_claim_may_name_either_player():
    handoff = ev(10, kind="handoff", player=None, item="onion", duration=3.0, giver=0, receiver=1)
    for p in ("P1", "P2"):
        assert statuses([cl(11, type_="handoff", player=p, text="passed an onion")], [handoff]) == ["supported"]


def _record(claims, events, deliveries_claimed=1):
    true = sum(e["kind"] == "delivery" for e in events)
    return {
        "trial_id": "x", "events": events, "behaviors": {},
        "conditions": {"video_dense": {"segments": [
            {"start": 0.0, "end": 60.0, "claims": claims, "deliveries_claimed": deliveries_claimed,
             "deliveries_true": true}]}},
    }


def test_recall_and_its_ceiling():
    events = [ev(t) for t in (5, 15, 25, 35)]
    counts = episode_counts(_record([cl(5), cl(15)], events), "video_dense", cap=2, draws=0)["counts"]
    assert counts["events"] == 4
    assert counts["events_recalled"] == 2
    assert counts["events_ceiling"] == 2  # only 2 claims allowed
    assert counts["recall_delivery_hit"] == 2


def test_clip_relative_times_are_caught():
    rec = _record([cl(5)], [ev(65)])
    rec["conditions"]["video_dense"]["segments"][0].update(start=60.0, end=120.0)
    counts = episode_counts(rec, "video_dense", cap=20, draws=0)["counts"]
    assert counts["before_window"] == 1
    assert counts["offset_rescued"] == 1


def test_actor_accuracy_ignores_the_named_player_when_matching():
    counts = episode_counts(_record([cl(10, player="P2")], [ev(10, player=0)]), "video_dense", cap=20,
                            draws=0)["counts"]
    assert counts["actor_checked"] == 1
    assert counts["actor_correct"] == 0


def test_random_time_baseline_is_about_the_share_of_the_minute_in_tolerance():
    counts = episode_counts(_record([cl(10)], [ev(10)]), "video_dense", cap=20, draws=2000)["counts"]
    assert counts["tol_3.0_random_supported"] == pytest.approx(0.1, abs=0.03)
