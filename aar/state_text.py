"""The raw game state as text, with no event abstraction.

This is the same information the video is drawn from, in words: where each
player stands, which way they face, what they hold, what is in each pot and on
each counter. The `state_text` condition reads it twice per second; the
perception probe's text form reads a single state.

It separates two things the pilot mixed together: "pixels vs. text" and "raw
state vs. a list of events someone already extracted".
"""
from __future__ import annotations

from .data_loader import Trial

_SOUP_COOK_TICKS = 20
_FACING = {(0, -1): "up", (0, 1): "down", (1, 0): "right", (-1, 0): "left"}

COORDS_NOTE = "Positions are (x, y) grid squares: x grows to the right, y grows downward."


def _held(player: dict) -> str:
    obj = player.get("held_object")
    return obj["name"] if obj else "nothing"


def pot_positions(terrain: list[list[str]]) -> list[tuple[int, int]]:
    return [(x, y) for y, row in enumerate(terrain) for x, ch in enumerate(row) if ch == "P"]


def pot_contents(state: dict, pots: list[tuple[int, int]]) -> dict[tuple[int, int], tuple[int, int]]:
    """Pot position -> (onions, cook_ticks); (0, 0) for an empty pot."""
    out = {pos: (0, 0) for pos in pots}
    for obj in state["objects"].values():
        pos = tuple(obj["position"])
        if obj["name"] == "soup" and pos in out:
            _, num, ticks = obj["state"]
            out[pos] = (int(num), int(ticks))
    return out


def _pot_phrase(num: int, ticks: int) -> str:
    if num == 0:
        return "empty"
    if ticks >= _SOUP_COOK_TICKS:
        return "soup ready"
    if ticks > 0:
        return f"cooking ({ticks}/{_SOUP_COOK_TICKS})"
    return f"{num} onion{'s' if num != 1 else ''}, not cooking"


def _loose_items(state: dict, pots: list[tuple[int, int]]) -> list[str]:
    return sorted(
        f"{obj['name']}@({obj['position'][0]},{obj['position'][1]})"
        for obj in state["objects"].values()
        if tuple(obj["position"]) not in pots
    )


def describe_state(state: dict, terrain: list[list[str]]) -> str:
    """One state as a few sentences, for the probe's text form."""
    pots = pot_positions(terrain)
    lines = [COORDS_NOTE]
    for i, p in enumerate(state["players"]):
        x, y = p["position"]
        facing = _FACING.get(tuple(p["orientation"]), "?")
        lines.append(f"P{i + 1} stands at ({x}, {y}), facing {facing}, holding {_held(p)}.")
    for pos, (num, ticks) in sorted(pot_contents(state, pots).items()):
        lines.append(f"Pot at ({pos[0]}, {pos[1]}): {_pot_phrase(num, ticks)}.")
    loose = _loose_items(state, pots)
    lines.append("On counters: " + (", ".join(loose) if loose else "nothing") + ".")
    return "\n".join(lines)


def state_row(state: dict, seconds: float, pots: list[tuple[int, int]]) -> str:
    parts = [f"t={seconds:6.1f}s"]
    for i, p in enumerate(state["players"]):
        x, y = p["position"]
        facing = _FACING.get(tuple(p["orientation"]), "?")
        parts.append(f"P{i + 1} ({x},{y}) {facing} holds {_held(p)}")
    pot_text = ", ".join(
        f"({pos[0]},{pos[1]}) {_pot_phrase(num, ticks)}" for pos, (num, ticks) in sorted(pot_contents(state, pots).items())
    )
    parts.append(f"pots: {pot_text}")
    loose = _loose_items(state, pots)
    if loose:
        parts.append("counters: " + " ".join(loose))
    return " | ".join(parts)


def segment_state_text(trial: Trial, terrain: list[list[str]], start: float, end: float, hz: float = 2.0) -> str:
    """The state every 1/hz seconds between start and end, one line each."""
    pots = pot_positions(terrain)
    lines = [f"Layout: {trial.layout_name}", f"This is seconds {start:.0f}-{end:.0f} of the episode.", COORDS_NOTE, ""]
    next_t = start
    for i, secs in enumerate(trial.time_elapsed):
        if secs < start or secs >= end:
            continue
        if secs + 1e-9 >= next_t:
            lines.append(state_row(trial.states[i], secs, pots))
            next_t += 1.0 / hz
            while next_t <= secs:
                next_t += 1.0 / hz
    return "\n".join(lines)
