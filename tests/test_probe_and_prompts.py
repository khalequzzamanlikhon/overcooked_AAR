"""Checks on the probe items, the prompts, the rendering refactor and the
review fact-check, against the bundled human data.

    python -m pytest tests -q
"""
from __future__ import annotations

import numpy as np
import pytest

from aar import prompts
from aar.aar_check import check_review, count_statements, timed_statements
from aar.data_loader import load_trials
from aar.probe import QTYPES, build_items, parse_answer, score
from aar.telemetry_to_text import events_to_timeline, extract_events


@pytest.fixture(scope="module")
def trials():
    return load_trials("clean_train_trials.pickle", layout="cramped_room")[:2]


def test_log_prompt_no_longer_gives_away_the_final_score(trials):
    trial = trials[0]
    events = extract_events(trial)
    assert "Final score" not in events_to_timeline(trial, events, 0, 60)
    assert "Final score" in events_to_timeline(trial, events, 0, 60, pilot_header=True)


def test_conditions_differ_only_in_the_source_block():
    common = prompts.RULES
    task = prompts.CLAIMS_TASK.format(start=60, end=120, cap=20)
    for condition in ("telemetry", "video_dense", "video_log", "state_text", "blind"):
        p = prompts.claims_prompt(condition, 60, 120, 20, log="LOG", state="STATE", layout="cramped_room")
        assert p.startswith(common) and p.endswith(task)


def test_probe_items_have_answers_from_the_state(trials):
    items = build_items([(t, "train") for t in trials], seed=1, n_frame=8, n_clip=4)
    assert {i["qtype"] for i in items} <= set(QTYPES)
    for item in items:
        if item["qtype"] == "L0_clock":
            trial = next(t for t in trials if t.trial_id == item["trial_id"])
            assert item["gold"] == int(trial.time_elapsed[item["input"]["i"]])
        if item["qtype"] == "L4_count":
            events = extract_events(next(t for t in trials if t.trial_id == item["trial_id"]))
            t0, t1 = item["input"]["t0"], item["input"]["t1"]
            assert item["gold"] == sum(1 for e in events if e.kind == "delivery" and t0 <= e.seconds < t1)
        if item["answer_type"] == "choice":
            assert item["gold"] in item["choices"]


def test_probe_builds_the_same_items_from_the_same_seed(trials):
    a = build_items([(t, "train") for t in trials], seed=3, n_frame=4, n_clip=2)
    b = build_items([(t, "train") for t in trials], seed=3, n_frame=4, n_clip=2)
    assert a == b


def test_answer_parsing():
    choice = {"answer_type": "choice", "choices": ["P1", "P2"], "gold": "P2"}
    assert parse_answer(choice, "Player 2 delivered it.") == "P2"
    assert parse_answer({"answer_type": "choice", "choices": ["yes", "no"]}, "No.") == "no"
    assert parse_answer({"answer_type": "int"}, "There were 3 soups") == 3
    loc = {"answer_type": "seconds", "gold": 42.0}
    assert score(loc, parse_answer(loc, "At t = 44.5 s")) == {"correct": True, "parsed": True, "abs_error": 2.5}
    assert score(choice, None) == {"correct": False, "parsed": False}


def test_render_refactor_draws_the_same_frame(trials):
    """FrameRenderer must draw exactly what the pilot's render loop drew."""
    from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
    from overcooked_ai_py.visualization.state_visualizer import StateVisualizer

    from aar import render_video as rv
    from aar.config import RenderConfig
    from aar.state_convert import convert_old_state

    trial, cfg, i = trials[0], RenderConfig(), 300
    mdp = OvercookedGridworld.from_layout_name(trial.layout_name, old_dynamics=True)
    surface = StateVisualizer(tile_size=cfg.tile_size).render_state(state=convert_old_state(trial.states[i]),
                                                                    grid=mdp.terrain_mtx)
    old = rv._surface_to_bgr(surface)
    rv._label_players(old, trial.states[i], cfg.tile_size, len(mdp.terrain_mtx))
    old = rv._add_clock_strip(old, trial.time_elapsed[i], trial.scores[i], cfg.clock_strip_px)
    assert np.array_equal(rv.render_frame(trial, i), old)


def test_output_cut_off_at_the_token_limit_keeps_the_finished_claims():
    from aar.generate_aar import _normalise
    from aar.vlm_local import parse_json

    raw = ('{"deliveries": 5,\n "claims": [\n {"time": 18.0, "player": "P1", "type": "delivery", "text": "P1 delivered."},\n'
           ' {"time": 36.0, "player": "P2", "type": "pickup", "text": "P2 picked up a dish."},\n {"time": 56.')
    got = _normalise(parse_json(raw), raw, cap=1)
    assert got["deliveries"] == 5 and got["truncated"] and not got["parse_failed"]
    assert [c["time"] for c in got["claims"]] == [18.0]  # the cap keeps the first
    assert got["claims_over_cap"] == 1


def test_review_fact_check():
    events = [{"t": 1, "seconds": s, "kind": "delivery", "player": p, "item": "soup", "text": "", "duration": 0.0,
               "extra": {}} for s, p in [(20.0, 0), (40.0, 0), (60.0, 1)]]
    assert count_statements("They made 3 deliveries; P1 delivered two soups.") == [3, 2]
    claims = timed_statements("P2 delivered a soup at t=60s. P1 picked up an onion.")
    assert claims == [{"time": 60.0, "player": "P2", "type": "delivery", "text": "P2 delivered a soup at t=60s."}]
    good = check_review("The team made 3 deliveries. P1 delivered a soup at 20 seconds.", events)
    assert good["count_errors"] == 0 and good["timed_errors"] == 0 and good["timed_statements"] == 1
    bad = check_review("P1 made 24 deliveries. P2 delivered a soup at t=30s.", events)
    assert bad["count_errors"] == 1 and bad["timed_errors"] == 1
