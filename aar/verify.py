"""Check each claim against the game log.

Only claims about things the log records can be checked this way: deliveries,
pickups, pot and counter interactions, blocked moves and standing still.
Claims about coordination or strategy are left for human raters -- marking
them right or wrong automatically would just be the log grading prose.

A claim is
  supported    an event of that type, by that player, within the tolerance
  wrong_time   that player did do it in this minute, but not near that time
  contradicted no such event by that player in this minute
  unchecked    not the kind of thing the log knows about
"""
from __future__ import annotations

from .config import CLAIM_TOLERANCE_S
from .telemetry_to_text import Event

# claim type -> event kinds that would support it
_TYPE_MAP = {
    "delivery": {"delivery"},
    "pickup": {"pickup", "fill_dish"},
    "pot": {"place_pot", "cook_start", "soup_ready", "fill_dish"},
    "counter": {"place_counter"},
    "blocked": {"blocked"},
    "idle": {"idle"},
}
_UNCHECKABLE = {"coordination", "strategy", "other", ""}
_ITEMS = ("onion", "dish", "soup")


def _player_index(claim_player: str) -> int | None:
    return {"P1": 0, "P2": 1}.get(claim_player.upper())


def _matches_player(event: Event, want: int | None) -> bool:
    if want is None or event.player is None:
        return True
    return event.player == want


def _matches_item(event: Event, text: str) -> bool:
    named = [i for i in _ITEMS if i in text.lower()]
    if not named or event.item is None:
        return True
    return event.item in named


def verify_claim(claim: dict, events: list[Event], tol: float = CLAIM_TOLERANCE_S) -> dict:
    kind_set = _TYPE_MAP.get(claim.get("type", ""), None)
    if kind_set is None or claim.get("type") in _UNCHECKABLE:
        return {"status": "unchecked", "reason": "not recorded in the log"}
    if claim.get("time") is None:
        return {"status": "unchecked", "reason": "no timestamp"}

    want_player = _player_index(claim.get("player", "both"))
    candidates = [
        e
        for e in events
        if e.kind in kind_set and _matches_player(e, want_player) and _matches_item(e, claim["text"])
    ]
    if not candidates:
        return {"status": "contradicted", "reason": "no such event by that player in this minute"}

    def distance(event: Event) -> float:
        if event.kind == "idle":  # a stretch, not an instant
            if event.seconds <= claim["time"] <= event.seconds + event.duration:
                return 0.0
            return min(abs(event.seconds - claim["time"]), abs(event.seconds + event.duration - claim["time"]))
        return abs(event.seconds - claim["time"])

    best = min(candidates, key=distance)
    gap = distance(best)
    if gap <= tol:
        return {"status": "supported", "reason": f"matched {best.kind} at t={best.seconds:.1f}s", "gap": round(gap, 1)}
    return {"status": "wrong_time", "reason": f"closest {best.kind} was {gap:.1f}s away", "gap": round(gap, 1)}


def verify_segment(claims: list[dict], events: list[Event]) -> list[dict]:
    return [dict(claim, verdict=verify_claim(claim, events)) for claim in claims]


def true_deliveries(events: list[Event]) -> int:
    return sum(1 for e in events if e.kind == "delivery")
