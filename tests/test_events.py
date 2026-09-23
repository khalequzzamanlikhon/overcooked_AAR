"""Checks on the event extractor, against the bundled human data.

    python -m pytest tests -q

These are the properties the whole comparison rests on: if the log is wrong,
the telemetry condition is being fed fiction and any result is meaningless.
"""
from __future__ import annotations

import pytest

from aar.config import SEGMENT_SECONDS
from aar.data_loader import load_trials
from aar.telemetry_to_text import extract_events, segment_bounds, segment_events
from aar.verify import true_deliveries

POINTS_PER_SOUP = 5  # what a delivered onion soup is worth in this 2019 data


@pytest.fixture(scope="module")
def trials():
    return load_trials("clean_train_trials.pickle", layout="cramped_room")[:3]


def test_delivery_count_matches_the_score(trials):
    for trial in trials:
        events = extract_events(trial)
        assert true_deliveries(events) == int(trial.final_score) // POINTS_PER_SOUP


def test_every_event_lands_in_exactly_one_segment(trials):
    """Slice with the same windows the pipeline uses. Slicing by hand up to
    240 s hid that the real last window stopped at 180."""
    for trial in trials:
        events = extract_events(trial)
        bounds = segment_bounds(trial.time_elapsed[-1], SEGMENT_SECONDS)
        sliced = [e for s, end in bounds for e in segment_events(events, s, end)]
        assert len(sliced) == len(events)
        assert true_deliveries(sliced) == true_deliveries(events)


def test_segment_bounds():
    assert segment_bounds(180.6, 60) == [(0, 60), (60, 120), (120, 181)]
    assert segment_bounds(180.0, 60) == [(0, 60), (60, 120), (120, 181)]
    assert segment_bounds(195.0, 60) == [(0, 60), (60, 120), (120, 180), (180, 196)]
    assert segment_bounds(30.0, 60) == [(0, 31)]


def test_blocked_events_are_rare(trials):
    """A real block needs the teammate on the target tile. The old version
    counted every press into a counter and produced hundreds per episode."""
    for trial in trials:
        events = extract_events(trial)
        blocked = [e for e in events if e.kind == "blocked"]
        assert len(blocked) < 0.1 * len(events)


def test_actions_are_aligned_to_the_next_state(trials):
    """The action at t moves the player from t to t+1. If that is off by one,
    most presses toward a free tile look like failed moves."""
    trial = trials[0]
    moved = attempts = 0
    for t in range(len(trial) - 1):
        for p in (0, 1):
            action = trial.joint_actions[t][p]
            if not isinstance(action, (list, tuple)) or tuple(action) == (0, 0):
                continue
            pos = tuple(trial.states[t]["players"][p]["position"])
            nxt = tuple(trial.states[t + 1]["players"][p]["position"])
            attempts += 1
            moved += (nxt[0] - pos[0], nxt[1] - pos[1]) == tuple(action)
    assert moved / attempts > 0.5
