"""Turn raw per-timestep state into an event list and a natural-language timeline.

This is the step that decides what the telemetry condition can possibly know.
An LLM cannot reason over 1,200 rows of coordinates; it reasons over events.

Two things matter for correctness and both were wrong in the first version:

1. The action at step t produces the move from t to t+1, not from t-1 to t.
   Matching it the other way marks ~78% of real moves as failures.
2. A blocked move is only a blocked move if the teammate is standing on the
   tile you tried to enter. Counting every press that does not move you also
   counts pressing into a counter, which is how you interact with a counter,
   so it fires constantly.

Events kept: pickups, placing an onion in a pot, placing anything on a
counter, filling a dish from a pot, deliveries, cooking started, soup ready,
blocked moves (merged) and idle stretches (merged).
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld

from .data_loader import Trial

logger = logging.getLogger(__name__)

# In the old dynamics a soup is done 20 ticks after the third onion goes in.
_SOUP_COOK_TICKS = 20
# A player who has not pressed anything for this many steps is standing still.
_IDLE_STEPS = 20  # ~3 s at 6.7 Hz
_INTERACT = "INTERACT"

# The 2019 study's layout names; the current package renamed two of them.
LAYOUT_ALIASES = {
    "random0": "forced_coordination",
    "random3": "counter_circuit_o_1order",
}

_ARTICLE = {"onion": "an onion", "dish": "a dish", "soup": "a soup", "tomato": "a tomato"}


@dataclass
class Event:
    """One thing that happened, with the clock time the video also shows."""

    t: int
    seconds: float
    kind: str  # pickup | place_pot | place_counter | fill_dish | delivery
    #            cook_start | soup_ready | blocked | idle
    player: int | None  # 0-based; None when the log does not attribute it
    item: str | None
    text: str
    duration: float = 0.0  # seconds, for merged blocked/idle stretches
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def terrain_for(trial: Trial) -> list[list[str]]:
    layout = LAYOUT_ALIASES.get(trial.layout_name, trial.layout_name)
    return OvercookedGridworld.from_layout_name(layout, old_dynamics=True).terrain_mtx


def _held(state: dict, player_idx: int) -> str | None:
    obj = state["players"][player_idx].get("held_object")
    return obj["name"] if obj else None


def _facing_tile(terrain: list[list[str]], player: dict) -> str:
    x, y = player["position"]
    dx, dy = player["orientation"]
    tx, ty = x + dx, y + dy
    if 0 <= ty < len(terrain) and 0 <= tx < len(terrain[ty]):
        return terrain[ty][tx]
    return " "


def _pots(state: dict) -> dict[tuple[int, int], tuple[str, int, int]]:
    """Pot position -> (ingredient, count, cook_ticks) for soups on the map."""
    out = {}
    for obj in state["objects"].values():
        if obj["name"] == "soup":
            ingredient, num, ticks = obj["state"]
            out[tuple(obj["position"])] = (ingredient, int(num), int(ticks))
    return out


def extract_events(trial: Trial) -> list[Event]:
    terrain = terrain_for(trial)
    events: list[Event] = []

    prev_held = [_held(trial.states[0], i) for i in (0, 1)]
    prev_score = trial.scores[0]
    prev_pots = _pots(trial.states[0])
    cooking: set[tuple[int, int]] = set()
    ready: set[tuple[int, int]] = set()
    score_bumps: list[tuple[int, float, int]] = []

    for t in range(1, len(trial)):
        state = trial.states[t]
        prev_state = trial.states[t - 1]
        secs = trial.time_elapsed[t]

        for p in (0, 1):
            now = _held(state, p)
            was = prev_held[p]
            if now == was:
                continue
            tile = _facing_tile(terrain, prev_state["players"][p])
            if was is None and now is not None:
                events.append(Event(t, secs, "pickup", p, now, f"P{p + 1} picked up {_ARTICLE[now]}."))
            elif was == "dish" and now == "soup":
                events.append(Event(t, secs, "fill_dish", p, "soup", f"P{p + 1} filled a dish with soup."))
            elif was is not None and now is None:
                if was == "soup" and tile == "S":
                    events.append(Event(t, secs, "delivery", p, "soup", f"P{p + 1} delivered a soup."))
                elif was == "onion" and tile == "P":
                    events.append(Event(t, secs, "place_pot", p, "onion", f"P{p + 1} put an onion in the pot."))
                else:
                    where = "a counter" if tile == "X" else "the floor"
                    events.append(
                        Event(t, secs, "place_counter", p, was, f"P{p + 1} put {_ARTICLE[was]} down on {where}.")
                    )
            prev_held[p] = now

        if trial.scores[t] > prev_score:
            score_bumps.append((t, secs, int(trial.scores[t] - prev_score)))
            prev_score = trial.scores[t]

        pots = _pots(state)
        for pos, (ingredient, num, ticks) in pots.items():
            was_pot = prev_pots.get(pos)
            if ticks > 0 and pos not in cooking:
                cooking.add(pos)
                events.append(Event(t, secs, "cook_start", None, ingredient, f"A pot started cooking ({num} onions)."))
            if ticks >= _SOUP_COOK_TICKS and pos not in ready:
                ready.add(pos)
                events.append(Event(t, secs, "soup_ready", None, ingredient, "A soup finished cooking."))
            if was_pot is None and ticks == 0 and num >= 1:
                pass  # the onion that created the soup object is already a place_pot event
        for pos in list(cooking):
            if pos not in pots:
                cooking.discard(pos)
                ready.discard(pos)
        prev_pots = pots

        # Blocked moves: the action at t moves the player from t to t+1.
        if t + 1 < len(trial):
            for p in (0, 1):
                action = trial.joint_actions[t][p]
                if not isinstance(action, (list, tuple)) or tuple(action) == (0, 0):
                    continue
                pos = tuple(state["players"][p]["position"])
                target = (pos[0] + action[0], pos[1] + action[1])
                mate = tuple(state["players"][1 - p]["position"])
                moved = tuple(trial.states[t + 1]["players"][p]["position"]) != pos
                if target == mate and not moved:
                    events.append(
                        Event(t, secs, "blocked", p, None, f"P{p + 1} tried to move into P{2 - p} and was blocked.")
                    )

    events += _idle_events(trial)
    events += _unattributed_deliveries(events, score_bumps)
    # Within one timestep: what a player did, then what that did to a pot.
    order = {"pickup": 0, "place_pot": 0, "place_counter": 0, "fill_dish": 0, "delivery": 0, "blocked": 1, "idle": 1}
    events.sort(key=lambda e: (e.t, order.get(e.kind, 2)))
    return _merge_blocked(events)


def _unattributed_deliveries(events: list[Event], bumps: list[tuple[int, float, int]]) -> list[Event]:
    """The score is ground truth for how many soups were served. Each bump
    should already have a `delivery` event within a step or two of it; if one
    does not, the log still has to show that a soup went out."""
    delivered = sorted((e for e in events if e.kind == "delivery"), key=lambda e: e.t)
    extra: list[Event] = []
    used: set[int] = set()
    for t, secs, points in bumps:
        match = None
        for i, event in enumerate(delivered):
            if i not in used and abs(event.t - t) <= 3:
                match = i
                break
        if match is None:
            extra.append(Event(t, secs, "delivery", None, "soup", f"A soup was delivered (+{points})."))
        else:
            used.add(match)
            delivered[match].extra["points"] = points
    return extra


def _idle_events(trial: Trial) -> list[Event]:
    """One event per stretch where a player pressed nothing at all."""
    out: list[Event] = []
    for p in (0, 1):
        run_start = None
        for t in range(len(trial.joint_actions)):
            action = trial.joint_actions[t][p]
            still = isinstance(action, (list, tuple)) and tuple(action) == (0, 0)
            if still and run_start is None:
                run_start = t
            elif not still and run_start is not None:
                _flush_idle(trial, p, run_start, t, out)
                run_start = None
        if run_start is not None:
            _flush_idle(trial, p, run_start, len(trial.joint_actions), out)
    return out


def _flush_idle(trial: Trial, p: int, start: int, end: int, out: list[Event]) -> None:
    if end - start < _IDLE_STEPS:
        return
    secs = trial.time_elapsed[start]
    duration = trial.time_elapsed[min(end, len(trial) - 1)] - secs
    out.append(
        Event(start, secs, "idle", p, None, f"P{p + 1} stood still for {duration:.0f} s.", duration=duration)
    )


def _merge_blocked(events: list[Event], gap_steps: int = 6) -> list[Event]:
    """Pressing into your teammate for a second is one event, not eight."""
    merged: list[Event] = []
    last_by_player: dict[int, Event] = {}
    for event in events:
        if event.kind == "blocked":
            last = last_by_player.get(event.player)
            if last is not None and event.t - last.extra.get("last_t", last.t) <= gap_steps:
                last.extra["last_t"] = event.t
                last.duration = round(event.seconds - last.seconds, 1)
                last.text = (
                    f"P{last.player + 1} tried to move into P{2 - last.player} and was blocked "
                    f"for {max(last.duration, 0.2):.1f} s."
                )
                continue
            event.extra["last_t"] = event.t
            last_by_player[event.player] = event
        merged.append(event)
    for event in merged:
        event.extra.pop("last_t", None)
    return merged


def segment_events(events: list[Event], start: float, end: float) -> list[Event]:
    return [e for e in events if start <= e.seconds < end]


def events_to_timeline(trial: Trial, events: list[Event], start: float, end: float) -> str:
    """Render one segment of the event list as text. Nothing is dropped."""
    lines = [
        f"Layout: {trial.layout_name}",
        f"Episode length: {trial.time_elapsed[-1]:.0f} s. This is seconds {start:.0f}-{end:.0f}.",
        f"Final score for the whole episode: {int(trial.final_score)}",
        "",
        "Event log:",
    ]
    rows = segment_events(events, start, end)
    lines += [f"  t={e.seconds:6.1f}s  {e.text}" for e in rows] or ["  (nothing was logged in this minute)"]
    return "\n".join(lines)
