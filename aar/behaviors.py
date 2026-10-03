"""Behaviours the raw state implies but the event log does not list.

The video is drawn from the same state as the log, so it cannot hold
information the state lacks. What it can show is behaviour nobody wrote down
as an event. These detectors compute three such behaviours from the raw state,
so a claim about them can be checked the same way a claim about a delivery is:

  waiting     a player stands still facing a pot while its soup cooks
  handoff     one player puts an item on a counter and the other picks it up
  congestion  the players stand side by side, both within 2 squares of the
              same station (pot, dispenser or serving hatch)

None of these are in the event log the `telemetry` condition reads. The
thresholds were set by eye on three episodes and then frozen; `scale`
multiplies every threshold so the analysis can report how much the numbers
move at 0.5x and 1.5x.
"""
from __future__ import annotations

from .data_loader import Trial
from .state_text import pot_contents, pot_positions
from .telemetry_to_text import Event

WAIT_MIN_S = 2.0  # standing at a cooking pot at least this long
HANDOFF_MAX_S = 10.0  # the other player picks the item up within this long
CONGESTION_MIN_S = 1.5  # side by side at the same station at least this long

_SOUP_COOK_TICKS = 20
_STATIONS = set("PODS")  # pot, onion dispenser, dish dispenser, serving hatch

BEHAVIOR_KINDS = ("waiting", "handoff", "congestion")


def _facing_pos(player: dict) -> tuple[int, int]:
    x, y = player["position"]
    dx, dy = player["orientation"]
    return x + dx, y + dy


def _tile(terrain: list[list[str]], pos: tuple[int, int]) -> str:
    x, y = pos
    if 0 <= y < len(terrain) and 0 <= x < len(terrain[y]):
        return terrain[y][x]
    return " "


def _held(state: dict, p: int) -> str | None:
    obj = state["players"][p].get("held_object")
    return obj["name"] if obj else None


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """[start, end) index ranges where flags is True."""
    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    return out


def _stretch(trial: Trial, start: int, end: int) -> tuple[float, float]:
    secs = trial.time_elapsed[start]
    return secs, trial.time_elapsed[min(end, len(trial) - 1)] - secs


def detect_waiting(trial: Trial, terrain: list[list[str]], scale: float = 1.0) -> list[Event]:
    pots = pot_positions(terrain)
    out = []
    for p in (0, 1):
        flags = []
        for i, state in enumerate(trial.states):
            player = state["players"][p]
            facing = _facing_pos(player)
            cooking = False
            if facing in pots:
                num, ticks = pot_contents(state, pots)[facing]
                cooking = 0 < ticks < _SOUP_COOK_TICKS
            still = i > 0 and tuple(player["position"]) == tuple(trial.states[i - 1]["players"][p]["position"])
            flags.append(cooking and (still or i == 0))
        for start, end in _runs(flags):
            secs, dur = _stretch(trial, start, end)
            if dur >= WAIT_MIN_S * scale:
                out.append(Event(start, secs, "waiting", p, None, f"P{p + 1} waited at a cooking pot for {dur:.0f} s.",
                                 duration=round(dur, 1)))
    return out


def detect_handoffs(trial: Trial, terrain: list[list[str]], scale: float = 1.0) -> list[Event]:
    placed: dict[tuple[int, int], tuple[str, int, int]] = {}  # counter -> (item, t, player)
    out = []
    for t in range(1, len(trial)):
        prev, state = trial.states[t - 1], trial.states[t]
        for p in (0, 1):
            was, now = _held(prev, p), _held(state, p)
            if was == now:
                continue
            spot = _facing_pos(prev["players"][p])
            if _tile(terrain, spot) != "X":
                continue
            if was is not None and now is None:
                placed[spot] = (was, t, p)
            elif was is None and now is not None and spot in placed:
                item, t_put, giver = placed.pop(spot)
                gap = trial.time_elapsed[t] - trial.time_elapsed[t_put]
                if giver != p and item == now and gap <= HANDOFF_MAX_S * scale:
                    out.append(
                        Event(t_put, trial.time_elapsed[t_put], "handoff", None, item,
                              f"P{giver + 1} left {item} on a counter and P{p + 1} picked it up {gap:.1f} s later.",
                              duration=round(gap, 1), extra={"giver": giver, "receiver": p})
                    )
    return out


def detect_congestion(trial: Trial, terrain: list[list[str]], scale: float = 1.0) -> list[Event]:
    stations = {(x, y) for y, row in enumerate(terrain) for x, ch in enumerate(row) if ch in _STATIONS}

    def near(pos: tuple[int, int]) -> set[tuple[int, int]]:
        # within 2 squares: most stations have a single floor square in front
        # of them, so "both adjacent to it" could never happen
        return {s for s in stations if abs(s[0] - pos[0]) + abs(s[1] - pos[1]) <= 2}

    flags = []
    for state in trial.states:
        a, b = (tuple(pl["position"]) for pl in state["players"])
        touching = abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
        flags.append(touching and bool(near(a) & near(b)))
    out = []
    for start, end in _runs(flags):
        secs, dur = _stretch(trial, start, end)
        if dur >= CONGESTION_MIN_S * scale:
            out.append(Event(start, secs, "congestion", None, None,
                             f"Both players crowded the same station for {dur:.0f} s.", duration=round(dur, 1)))
    return out


def detect_behaviors(trial: Trial, terrain: list[list[str]], scale: float = 1.0) -> list[Event]:
    events = detect_waiting(trial, terrain, scale) + detect_handoffs(trial, terrain, scale) + detect_congestion(
        trial, terrain, scale
    )
    return sorted(events, key=lambda e: (e.t, e.kind))
