"""Checks on the derived-behaviour detectors, on hand-built trajectories.

    python -m pytest tests -q
"""
from __future__ import annotations

from aar.behaviors import detect_congestion, detect_handoffs, detect_waiting
from aar.data_loader import Trial

# cramped_room: pot at (2,0), onion dispensers at (0,1) and (4,1),
# dish dispenser at (1,3), serving hatch at (3,3), counters X
CRAMPED = [list("XXPXX"), list("O   O"), list("X   X"), list("XDXSX")]
UP, DOWN, LEFT = (0, -1), (0, 1), (-1, 0)
DT = 0.15  # ~6.7 Hz, like the data


def player(pos, facing=UP, held=None):
    return {"position": list(pos), "orientation": list(facing),
            "held_object": None if held is None else {"name": held, "position": list(pos)}}


def state(p1, p2, pot_ticks=None):
    objects = {}
    if pot_ticks is not None:
        objects["2,0"] = {"name": "soup", "position": [2, 0], "state": ["onion", 3, pot_ticks]}
    return {"players": [p1, p2], "objects": objects}


def trial(states):
    n = len(states)
    return Trial("toy", "cramped_room", 0.0, states, [[(0, 0), (0, 0)]] * n, [0.0] * n, [i * DT for i in range(n)])


def test_waiting_at_a_cooking_pot():
    # P1 stands under the pot for 20 steps (3 s) while it cooks; P2 is elsewhere
    states = [state(player((2, 1), UP), player((1, 2)), pot_ticks=5 + i // 7) for i in range(20)]
    events = detect_waiting(trial(states), CRAMPED)
    assert [(e.kind, e.player) for e in events] == [("waiting", 0)]
    assert events[0].duration >= 2.0


def test_no_waiting_when_the_pot_is_not_cooking():
    states = [state(player((2, 1), UP), player((1, 2))) for _ in range(20)]
    assert detect_waiting(trial(states), CRAMPED) == []


def test_waiting_needs_two_seconds():
    states = [state(player((2, 1), UP), player((1, 2)), pot_ticks=5) for _ in range(10)]  # 1.35 s
    assert detect_waiting(trial(states), CRAMPED) == []


def test_handoff_across_a_counter():
    # P1 at (2,2) puts an onion on the counter at (2,3); P2 takes it 2 s later
    s = [state(player((2, 2), DOWN, "onion"), player((3, 1)))]
    s += [state(player((2, 2), DOWN), player((3, 1)))]
    s += [state(player((1, 2), LEFT), player((3, 2)))] * 10
    s += [state(player((1, 2), LEFT), player((2, 2), DOWN))] * 3
    s += [state(player((1, 2), LEFT), player((2, 2), DOWN, "onion"))]
    events = detect_handoffs(trial(s), CRAMPED)
    assert len(events) == 1
    assert events[0].extra == {"giver": 0, "receiver": 1}
    assert events[0].item == "onion"


def test_picking_your_own_item_back_up_is_not_a_handoff():
    s = [state(player((2, 2), DOWN, "onion"), player((3, 1))), state(player((2, 2), DOWN), player((3, 1))),
         state(player((2, 2), DOWN, "onion"), player((3, 1)))]
    assert detect_handoffs(trial(s), CRAMPED) == []


def test_congestion_side_by_side_at_the_pot():
    s = [state(player((2, 1)), player((3, 1))) for _ in range(15)]  # ~2 s, both near the pot
    events = detect_congestion(trial(s), CRAMPED)
    assert [e.kind for e in events] == ["congestion"]


def test_no_congestion_when_apart():
    s = [state(player((1, 1)), player((3, 2))) for _ in range(15)]
    assert detect_congestion(trial(s), CRAMPED) == []


def test_scale_moves_the_threshold():
    states = [state(player((2, 1), UP), player((1, 2)), pot_ticks=5) for _ in range(12)]  # ~1.65 s
    assert detect_waiting(trial(states), CRAMPED) == []
    assert len(detect_waiting(trial(states), CRAMPED, scale=0.5)) == 1
