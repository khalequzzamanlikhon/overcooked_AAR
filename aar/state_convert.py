"""Convert 2019-format state dicts into current `OvercookedState` objects.

`OvercookedState.from_dict` does NOT work on this data -- it fails with
`TypeError: string indices must be integers`. Two format changes since 2019:

  - `objects` was a dict keyed by "x,y"; it's now a list.
  - soups were `{'name': 'soup', 'state': ['onion', num, cook_ticks]}`;
    they're now full `SoupState` objects with an ingredient list.

Cooking constant: in the old dynamics a soup is done at 20 ticks.
"""
from __future__ import annotations

from overcooked_ai_py.mdp.overcooked_mdp import (
    ObjectState,
    OvercookedState,
    PlayerState,
    SoupState,
)

_SOUP_COOK_TICKS = 20


def _build_soup(obj: dict) -> SoupState:
    ingredient, num, cook_ticks = obj["state"]
    position = tuple(obj["position"])
    return SoupState.get_soup(
        position,
        num_onions=num if ingredient == "onion" else 0,
        num_tomatoes=num if ingredient == "tomato" else 0,
        cooking_tick=cook_ticks if cook_ticks > 0 else -1,
        finished=cook_ticks >= _SOUP_COOK_TICKS,
    )


def _build_object(obj: dict) -> ObjectState | SoupState:
    if obj["name"] == "soup":
        return _build_soup(obj)
    return ObjectState(obj["name"], tuple(obj["position"]))


def convert_old_state(state_dict: dict) -> OvercookedState:
    players = []
    for p in state_dict["players"]:
        held = _build_object(p["held_object"]) if p.get("held_object") else None
        players.append(PlayerState(tuple(p["position"]), tuple(p["orientation"]), held))

    objects = [_build_object(o) for o in state_dict["objects"].values()]
    return OvercookedState(
        players,
        {o.position: o for o in objects},
        all_orders=[{"ingredients": ["onion", "onion", "onion"]}],
    )
