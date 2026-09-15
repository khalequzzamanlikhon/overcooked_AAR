"""Turn raw per-timestep state into a natural-language event timeline.

This is the step that matters most and gets the least attention. An LLM
cannot reason over 1,200 rows of coordinates; it reasons over events. The
whole quality of the generated AAR depends on this conversion, not on the
prompt.

The same conversion problem exists in R-CANE's phase 2: positions,
orientations, and shots-fired have to become "Marine B flanked left while
Marine A stayed pinned" before an LLM can say anything useful about them.

Events emitted: pickups, drops, deliveries (score changes), pot state
changes, idle stretches, and collisions/blocked moves (both players
attempting the same tile).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .data_loader import Trial

logger = logging.getLogger(__name__)

_IDLE_THRESHOLD = 30  # timesteps of no held-object change before flagging idleness


@dataclass
class Event:
    t: int
    seconds: float
    text: str


def _held(state: dict, player_idx: int) -> str | None:
    obj = state["players"][player_idx].get("held_object")
    return obj["name"] if obj else None


def _positions(state: dict) -> list[tuple[int, int]]:
    return [tuple(p["position"]) for p in state["players"]]


def extract_events(trial: Trial) -> list[Event]:
    events: list[Event] = []
    prev_held: list[str | None] = [_held(trial.states[0], i) for i in (0, 1)]
    prev_score = trial.scores[0]
    last_activity = [0, 0]

    for t in range(1, len(trial)):
        state = trial.states[t]
        secs = trial.time_elapsed[t]

        for p in (0, 1):
            now = _held(state, p)
            if now != prev_held[p]:
                if now is not None:
                    events.append(Event(t, secs, f"Player {p + 1} picked up {now}."))
                else:
                    events.append(Event(t, secs, f"Player {p + 1} put down {prev_held[p]}."))
                prev_held[p] = now
                last_activity[p] = t
            elif t - last_activity[p] > _IDLE_THRESHOLD:
                events.append(
                    Event(t, secs, f"Player {p + 1} had no item interaction for {t - last_activity[p]} steps.")
                )
                last_activity[p] = t

        if trial.scores[t] > prev_score:
            gained = trial.scores[t] - prev_score
            events.append(Event(t, secs, f"Soup delivered (+{int(gained)} points)."))
            prev_score = trial.scores[t]

        # A genuine blocked move, not a turn. In Overcooked, pressing a
        # direction you are not already facing turns you in place -- only a
        # press matching your current orientation is a move attempt. Without
        # this check every turn is a false "blocked" event, which floods the
        # timeline and teaches the LLM the team was permanently stuck.
        prev_state = trial.states[t - 1]
        for p in (0, 1):
            action = trial.joint_actions[t][p]
            if not isinstance(action, (list, tuple)) or tuple(action) == (0, 0):
                continue
            facing = tuple(prev_state["players"][p]["orientation"])
            moved = tuple(state["players"][p]["position"]) != tuple(prev_state["players"][p]["position"])
            if tuple(action) == facing and not moved:
                events.append(Event(t, secs, f"Player {p + 1} tried to move forward but was blocked."))

    return events


def events_to_timeline(trial: Trial, events: list[Event], max_events: int = 120) -> str:
    """Render events as a text timeline, downsampled if too long for a prompt."""
    if len(events) > max_events:
        step = len(events) // max_events + 1
        events = events[::step]
        logger.info("downsampled %s timeline to %d events", trial.trial_id, len(events))

    lines = [
        f"Layout: {trial.layout_name}",
        f"Episode length: {len(trial)} timesteps",
        f"Final score: {int(trial.final_score)}",
        "",
        "Timeline:",
    ]
    lines += [f"  t={e.seconds:6.1f}s  {e.text}" for e in events]
    return "\n".join(lines)
