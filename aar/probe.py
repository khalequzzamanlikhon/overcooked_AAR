"""Perception probe: where does reading the video break?

The pilot showed that the video model's timestamps score no better than random
times. That can fail at several places: the model cannot read the frame, cannot
tell who is who, cannot spot an event, cannot place it in time, or cannot add
events up. The probe asks one short question per item, level by level, with
every answer computed from the state log (no labelling):

  L0  reading          clock, score                         (1 frame)
  L1  one frame        what P1 holds, who holds X, left/right, pot onions, pot state
  L2  detection        did P1 deliver in this clip, who delivered   (5 s clip)
  L3  time             which of two events came first (10 s), when was the soup delivered (15 s)
  L4  counting         how many soups in this clip   (10 / 30 / 60 s)

Each item from L1 up is also asked with the same information as text (the
state described in words for one frame, the event log for a clip): the
same-information control. If text is right and video is wrong, the gap is
perception, not reasoning.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from pathlib import Path

from . import prompts
from .data_loader import Trial
from .state_text import describe_state, pot_contents, pot_positions
from .telemetry_to_text import events_to_timeline, extract_events, terrain_for

LEVELS = {
    "L0_clock": "L0", "L0_score": "L0",
    "L1_held": "L1", "L1_who_holds": "L1", "L1_relpos": "L1", "L1_pot_onions": "L1", "L1_pot_state": "L1",
    "L2_detect": "L2", "L2_actor": "L2",
    "L3_order": "L3", "L3_localize": "L3",
    "L4_count": "L4",
}
QTYPES = tuple(LEVELS)
FRAME_TYPES = {q for q in QTYPES if q.startswith(("L0", "L1"))}
CLIP_TYPES = set(QTYPES) - FRAME_TYPES
VIDEO_ONLY = {"L0_clock", "L0_score"}  # as text the answer is just printed

# (form, hud, fps) run on every model. `main` is the reference setting.
VARIANTS: dict[str, tuple[str, str, float]] = {
    "video_main": ("video", "full", 2.0),
    "text": ("text", "", 0.0),
    "video_fps0.33": ("video", "full", 1 / 3),
    "video_fps1": ("video", "full", 1.0),
    "video_fps4": ("video", "full", 4.0),
    "video_hud_clock": ("video", "clock", 2.0),  # no score on screen
    "video_hud_none": ("video", "none", 2.0),  # no clock or score
}
HUD_ABLATION_TYPES = {"L2_detect", "L3_localize", "L4_count"}
LOCALIZE_TOL_S = 3.0


def variant_types(variant: str) -> set[str]:
    form, hud, fps = VARIANTS[variant]
    if form == "text":
        return set(QTYPES) - VIDEO_ONLY
    if variant == "video_main":
        return set(QTYPES)
    if variant.startswith("video_fps"):
        return set(CLIP_TYPES)
    return set(HUD_ABLATION_TYPES)


def _held(state: dict, p: int) -> str:
    obj = state["players"][p].get("held_object")
    return obj["name"] if obj else "nothing"


def _pot_state(state: dict, pots) -> str:
    contents = pot_contents(state, pots).values()
    if any(t >= 20 for _, t in contents):
        return "ready"
    if any(t > 0 for _, t in contents):
        return "cooking"
    return "none"


class _Episode:
    def __init__(self, trial: Trial, split: str):
        self.trial, self.split = trial, split
        self.terrain = terrain_for(trial)
        self.pots = pot_positions(self.terrain)
        self.events = extract_events(trial)
        self.duration = trial.time_elapsed[-1]

    def base(self, qtype: str) -> dict:
        t = self.trial
        return {"qtype": qtype, "level": LEVELS[qtype], "trial_id": t.trial_id, "split": self.split,
                "layout": t.layout_name}

    def frame_item(self, qtype: str, i: int, question: str, fmt: str, gold, answer_type: str, choices=None) -> dict:
        state = self.trial.states[i]
        return self.base(qtype) | {
            "input": {"kind": "frame", "i": i, "seconds": round(self.trial.time_elapsed[i], 2)},
            "question": question, "fmt": fmt, "gold": gold, "answer_type": answer_type, "choices": choices,
            "text_input": None if qtype in VIDEO_ONLY else describe_state(state, self.terrain),
        }

    def clip_item(self, qtype: str, t0: float, t1: float, question: str, fmt: str, gold, answer_type: str,
                  choices=None) -> dict:
        return self.base(qtype) | {
            "input": {"kind": "clip", "t0": round(t0, 2), "t1": round(t1, 2)},
            "question": question, "fmt": fmt, "gold": gold, "answer_type": answer_type, "choices": choices,
            "text_input": events_to_timeline(self.trial, self.events, t0, t1),
        }

    def attributed(self, kinds: set[str]) -> list:
        return [e for e in self.events if e.kind in kinds and e.player is not None]


_ARTICLE = {"onion": "an onion", "dish": "a dish", "soup": "a soup"}


def _make_frame(ep: _Episode, qtype: str, rng: random.Random) -> dict | None:
    t = ep.trial
    i = rng.randrange(len(t))
    state = t.states[i]
    if qtype == "L0_clock":
        return ep.frame_item(qtype, i, "What episode time does the clock at the top show, in whole seconds?",
                             "a whole number", int(t.time_elapsed[i]), "int")
    if qtype == "L0_score":
        return ep.frame_item(qtype, i, "What score is shown at the top?", "a whole number", int(t.scores[i]), "int")
    if qtype == "L1_held":
        p = rng.randrange(2)
        return ep.frame_item(qtype, i, f"What is P{p + 1} holding?", "one of: nothing, onion, dish, soup",
                             _held(state, p), "choice", ["nothing", "onion", "dish", "soup"])
    if qtype == "L1_who_holds":
        held = [_held(state, 0), _held(state, 1)]
        items = [h for h in held if h != "nothing" and held.count(h) == 1]
        if not items:
            return None
        item = rng.choice(items)
        return ep.frame_item(qtype, i, f"Which player is holding {_ARTICLE[item]}?", "P1 or P2",
                             f"P{held.index(item) + 1}", "choice", ["P1", "P2"])
    if qtype == "L1_relpos":
        x1, x2 = state["players"][0]["position"][0], state["players"][1]["position"][0]
        if x1 == x2:
            return None
        return ep.frame_item(qtype, i, "Is P1 to the left or to the right of P2?", "left or right",
                             "left" if x1 < x2 else "right", "choice", ["left", "right"])
    if qtype == "L1_pot_onions":
        most = max((n for n, _ in pot_contents(state, ep.pots).values()), default=0)
        return ep.frame_item(qtype, i, "What is the largest number of onions in any one pot?", "a whole number from 0 to 3",
                             int(most), "int")
    if qtype == "L1_pot_state":
        return ep.frame_item(qtype, i, "Is a soup cooking or ready in any pot?",
                             "one of: none, cooking, ready (ready if any soup is done)", _pot_state(state, ep.pots),
                             "choice", ["none", "cooking", "ready"])
    raise ValueError(qtype)


def _window(center: float, length: float, duration: float, rng: random.Random, margin: float = 1.0) -> tuple[float, float]:
    lo = max(0.0, center - length + margin)
    hi = min(duration - length, center - margin)
    if hi < lo:
        lo = hi = max(0.0, min(center - length / 2, duration - length))
    t0 = rng.uniform(lo, hi)
    return t0, t0 + length


def _in(events, t0, t1):
    return [e for e in events if t0 <= e.seconds < t1]


def _make_clip(ep: _Episode, qtype: str, rng: random.Random, want=None) -> dict | None:
    dur = ep.duration
    deliveries = [e for e in ep.events if e.kind == "delivery"]
    if qtype == "L2_detect":
        p = rng.randrange(2)
        mine = [e for e in deliveries if e.player == p]
        if want == "yes":
            if not mine:
                return None
            t0, t1 = _window(rng.choice(mine).seconds, 5.0, dur, rng)
        else:
            t0 = rng.uniform(0, dur - 5.0)
            t1 = t0 + 5.0
        gold = "yes" if _in(mine, t0, t1) else "no"
        if want and gold != want:
            return None
        return ep.clip_item(qtype, t0, t1, f"Did P{p + 1} deliver a soup in this clip?", "yes or no", gold, "choice",
                            ["yes", "no"])
    if qtype == "L2_actor":
        attributed = [e for e in deliveries if e.player is not None]
        if not attributed:
            return None
        t0, t1 = _window(rng.choice(attributed).seconds, 5.0, dur, rng)
        inside = _in(deliveries, t0, t1)
        if len(inside) != 1 or inside[0].player is None:
            return None
        return ep.clip_item(qtype, t0, t1, "Who delivered the soup in this clip?", "P1 or P2",
                            f"P{inside[0].player + 1}", "choice", ["P1", "P2"])
    if qtype == "L3_order":
        pool = ep.attributed({"pickup", "place_pot", "place_counter", "delivery", "fill_dish"})
        if len(pool) < 2:
            return None
        a = rng.choice(pool)
        t0 = rng.uniform(max(0.0, a.seconds - 9.0), min(a.seconds - 0.5, dur - 10.0)) if a.seconds > 0.5 else 0.0
        t1 = t0 + 10.0
        inside = _in(pool, t0, t1)
        sig = Counter((e.kind, e.player, e.item) for e in inside)
        unique = [e for e in inside if sig[(e.kind, e.player, e.item)] == 1]
        pairs = [(x, y) for x in unique for y in unique if y.seconds - x.seconds >= 1.5]
        if not pairs:
            return None
        first, second = rng.choice(pairs)
        options = [first, second]
        rng.shuffle(options)
        gold = "A" if options[0] is first else "B"
        question = ("Which happened first? (A) " + options[0].text.rstrip(".") + ". (B) " + options[1].text.rstrip(".") + ".")
        return ep.clip_item(qtype, t0, t1, question, "A or B", gold, "choice", ["A", "B"])
    if qtype == "L3_localize":
        if not deliveries:
            return None
        t0, t1 = _window(rng.choice(deliveries).seconds, 15.0, dur, rng, margin=1.5)
        inside = _in(deliveries, t0, t1)
        if len(inside) != 1:
            return None
        return ep.clip_item(qtype, t0, t1, "At what episode time was the soup delivered, in seconds, as on the "
                            "episode clock?", "a number of seconds", round(inside[0].seconds, 2), "seconds")
    if qtype == "L4_count":
        length = want or 30.0
        t0 = rng.uniform(0, dur - length)
        t1 = t0 + length
        return ep.clip_item(qtype, t0, t1, "How many soups were delivered in this clip?", "a whole number",
                            len(_in(deliveries, t0, t1)), "int")
    raise ValueError(qtype)


def build_items(trials: list[tuple[Trial, str]], seed: int = 0, n_frame: int = 150, n_clip: int = 120) -> list[dict]:
    """Stratified: episodes are drawn round-robin by layout; classes are balanced
    where the answer is a class (held item, pot state, yes/no)."""
    rng = random.Random(seed)
    episodes = [_Episode(t, split) for t, split in trials]
    by_layout: dict[str, list[_Episode]] = {}
    for ep in episodes:
        by_layout.setdefault(ep.trial.layout_name, []).append(ep)
    layouts = sorted(by_layout)

    def draw(k: int) -> _Episode:
        return rng.choice(by_layout[layouts[k % len(layouts)]])

    items: list[dict] = []
    for qtype in QTYPES:
        n = n_frame if qtype in FRAME_TYPES else n_clip
        quotas: dict | None = None
        if qtype == "L1_held":
            quotas = {c: n // 4 for c in ("nothing", "onion", "dish", "soup")}
        elif qtype == "L1_pot_state":
            quotas = {c: n // 3 for c in ("none", "cooking", "ready")}
        elif qtype == "L1_pot_onions":
            quotas = {c: n // 4 for c in (0, 1, 2, 3)}
        elif qtype in ("L1_who_holds", "L2_actor"):
            quotas = {c: n // 2 for c in ("P1", "P2")}
        elif qtype == "L1_relpos":
            quotas = {c: n // 2 for c in ("left", "right")}
        elif qtype == "L3_order":
            quotas = {c: n // 2 for c in ("A", "B")}
        got: list[dict] = []
        tries = 0
        while len(got) < n and tries < n * 400:
            tries += 1
            ep = draw(tries)
            if qtype == "L2_detect":
                item = _make_clip(ep, qtype, rng, want="yes" if len(got) % 2 == 0 else "no")
            elif qtype == "L4_count":
                item = _make_clip(ep, qtype, rng, want=(10.0, 30.0, 60.0)[len(got) % 3])
            elif qtype in FRAME_TYPES:
                item = _make_frame(ep, qtype, rng)
            else:
                item = _make_clip(ep, qtype, rng)
            if item is None:
                continue
            if quotas is not None:
                if quotas.get(item["gold"], 0) <= 0:
                    continue
                quotas[item["gold"]] -= 1
            got.append(item)
        items += got
    for k, item in enumerate(items):
        item["id"] = f"{item['qtype']}_{k:05d}"
    return items


# ---------------------------------------------------------------- media


def media_path(item: dict, hud: str, root: Path) -> Path:
    inp = item["input"]
    if inp["kind"] == "frame":
        return root / hud / "frames" / f"{item['trial_id']}_{inp['i']}.png"
    return root / hud / "clips" / f"{item['trial_id']}_{inp['t0']:.2f}_{inp['t1']:.2f}.mp4"


def ensure_media(item: dict, renderer, hud: str, root: Path) -> Path:
    """Render the frame or clip for this item once; `renderer` is a FrameRenderer with that hud."""
    import cv2

    from .render_video import render_clip

    path = media_path(item, hud, root)
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    inp = item["input"]
    if inp["kind"] == "frame":
        cv2.imwrite(str(path), renderer.frame(inp["i"]))
    else:
        render_clip(renderer.trial, inp["t0"], inp["t1"], path, renderer=renderer)
    return path


# ---------------------------------------------------------------- prompts and scoring


def prompt_for(item: dict, form: str, hud: str = "full") -> str:
    inp = item["input"]
    if inp["kind"] == "frame":
        what = "picture of one moment of the game" if form == "video" else "state at one moment"
    else:
        what = (f"video clip, which covers seconds {inp['t0']:.0f}-{inp['t1']:.0f} of the episode"
                if form == "video" else f"events between seconds {inp['t0']:.0f} and {inp['t1']:.0f}")
    source = (prompts.PROBE_SOURCE_VIDEO.format(what=what) if form == "video"
              else prompts.PROBE_SOURCE_TEXT.format(what=what, text=item["text_input"]))
    return f"{prompts.PROBE_PREAMBLE}{source}\n\n{item['question']}\n{prompts.PROBE_ANSWER.format(fmt=item['fmt'])}"


_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def parse_answer(item: dict, raw: str):
    text = raw.strip()
    kind = item["answer_type"]
    if kind in ("int", "seconds"):
        m = _NUMBER.search(text)
        if not m:
            return None
        return int(float(m.group(0))) if kind == "int" else float(m.group(0))
    low = text.lower().replace("player 1", "p1").replace("player 2", "p2")
    hits = []
    for choice in item["choices"]:
        m = re.search(rf"\b{re.escape(choice.lower())}\b", low)
        if m:
            hits.append((m.start(), choice))
    return min(hits)[1] if hits else None


def score(item: dict, answer) -> dict:
    if answer is None:
        return {"correct": False, "parsed": False}
    if item["answer_type"] == "seconds":
        err = abs(float(answer) - float(item["gold"]))
        return {"correct": err <= LOCALIZE_TOL_S, "parsed": True, "abs_error": round(err, 2)}
    return {"correct": answer == item["gold"], "parsed": True}


def chance(item_group: list[dict]) -> dict:
    """What guessing would score on these items: uniform over the choices, the
    majority answer, and for localisation a uniform time in the clip."""
    golds = [it["gold"] for it in item_group]
    first = item_group[0]
    out = {"majority": round(Counter(golds).most_common(1)[0][1] / len(golds), 4)}
    if first["answer_type"] == "choice":
        out["uniform"] = round(1 / len(first["choices"]), 4)
    if first["answer_type"] == "seconds":
        hits = []
        for it in item_group:
            t0, t1, g = it["input"]["t0"], it["input"]["t1"], it["gold"]
            lo, hi = max(t0, g - LOCALIZE_TOL_S), min(t1, g + LOCALIZE_TOL_S)
            hits.append(max(hi - lo, 0) / (t1 - t0))
        out["uniform"] = round(sum(hits) / len(hits), 4)
    return out
