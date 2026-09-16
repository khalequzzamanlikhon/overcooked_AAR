"""Checks on the event extractor, against the bundled human data.

    python -m pytest tests -q

These are the properties the whole comparison rests on: if the log is wrong,
the telemetry condition is being fed fiction and any result is meaningless.
"""
from __future__ import annotations

import pytest

from aar.data_loader import load_trials
from aar.telemetry_to_text import extract_events, segment_events
from aar.verify import true_deliveries

POINTS_PER_SOUP = 5  # what a delivered onion soup is worth in this 2019 data


@pytest.fixture(scope="module")
def trials():
    return load_trials("clean_train_trials.pickle", layout="cramped_room")[:3]


def test_delivery_count_matches_the_score(trials):
    for trial in trials:
        events = extract_events(trial)
        assert true_deliveries(events) == int(trial.final_score) // POINTS_PER_SOUP


def test_every_delivery_reaches_the_timeline(trials):
    """Segments cover the episode, so no delivery may be dropped by slicing."""
    for trial in trials:
        events = extract_events(trial)
        in_segments = sum(
            true_deliveries(segment_events(events, s, s + 60)) for s in (0, 60, 120, 180)
        )
        assert in_segments == true_deliveries(events)


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
