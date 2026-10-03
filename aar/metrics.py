"""Study-v2 scoring: one-to-one matching, recall, time and actor accuracy.

The pilot's checker (`verify.py`, kept as the legacy scorer) matched each claim
to its nearest event on its own, so two claims next to one delivery could both
be "supported" by it. Here claims and events are matched one-to-one, per
minute, with the Hungarian algorithm on the time gap:

  supported     matched to an event of that type, by that player, within tol
  duplicate     such an event is within tol, but another claim already took it
  wrong_time    that player did do it this minute, but not within tol
  contradicted  no such event by that player this minute
  unchecked     not the kind of thing the state records, or no time given

Because each event can back only one claim, recall is now well defined: the
share of true events some claim was matched to.

Everything here is counted per episode, so `stats.py` can bootstrap over
episodes.
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from .config import CLAIM_TOLERANCE_S

# claim type -> event kinds that can back it. `pickup` no longer accepts
# fill_dish (taking soup out of a pot is a pot interaction).
TYPE_KINDS: dict[str, set[str]] = {
    "delivery": {"delivery"},
    "pickup": {"pickup"},
    "pot": {"place_pot", "fill_dish", "cook_start", "soup_ready"},
    "counter": {"place_counter"},
    "blocked": {"blocked"},
    "idle": {"idle"},
    "waiting": {"waiting"},
    "handoff": {"handoff"},
    "congestion": {"congestion"},
}
PICKUP_INCL_FILL = dict(TYPE_KINDS, pickup={"pickup", "fill_dish"})

# event kinds recall is counted over, grouped by the claim type that covers them
RECALL_KINDS: dict[str, tuple[str, ...]] = {
    "delivery": ("delivery",),
    "pickup": ("pickup",),
    "pot": ("place_pot", "fill_dish"),
    "counter": ("place_counter",),
    "blocked": ("blocked",),
    "idle": ("idle",),
    "waiting": ("waiting",),
    "handoff": ("handoff",),
    "congestion": ("congestion",),
}
BEHAVIOR_TYPES = ("waiting", "handoff", "congestion")
_ITEMS = ("onion", "dish", "soup")
_INF = 1e6
TOLERANCES = (0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0)
TIME_ERROR_WINDOW_S = 15.0


# ---------------------------------------------------------------- matching


def _player_ok(event: dict, claim_player: str) -> bool:
    want = {"P1": 0, "P2": 1}.get(claim_player)
    if want is None:  # "both" / "unclear": matches either player, reported on its own
        return True
    if event["kind"] == "handoff":
        return want in (event["extra"].get("giver"), event["extra"].get("receiver"))
    return event["player"] is None or event["player"] == want


def _item_ok(event: dict, text: str) -> bool:
    named = [i for i in _ITEMS if i in text.lower()]
    return not named or event.get("item") is None or event["item"] in named


def compatible(claim: dict, event: dict, type_kinds: dict = TYPE_KINDS, ignore_player: bool = False) -> bool:
    kinds = type_kinds.get(claim.get("type", ""))
    if not kinds or event["kind"] not in kinds:
        return False
    if not ignore_player and not _player_ok(event, claim.get("player", "UNCLEAR")):
        return False
    return _item_ok(event, claim.get("text", ""))


def gap(event: dict, t: float) -> float:
    """Seconds from t to the event; 0 inside a stretch (idle, waiting, ...)."""
    start = event["seconds"]
    end = start + max(event.get("duration") or 0.0, 0.0)
    return max(start - t, 0.0, t - end)


def checkable(claim: dict, type_kinds: dict = TYPE_KINDS) -> bool:
    return claim.get("type") in type_kinds and claim.get("time") is not None


def match_segment(claims: list[dict], events: list[dict], tol: float = CLAIM_TOLERANCE_S,
                  type_kinds: dict = TYPE_KINDS, times: list[float] | None = None) -> list[dict]:
    """One verdict per claim. `times` overrides the claims' own times (baselines)."""
    times = times if times is not None else [c.get("time") for c in claims]
    rows = [i for i, c in enumerate(claims) if c.get("type") in type_kinds and times[i] is not None]
    verdicts: list[dict] = [
        {"status": "unchecked", "event": None, "gap": None} for _ in claims
    ]
    if not rows:
        return verdicts
    compat = np.array([[compatible(claims[i], e, type_kinds) for e in events] for i in rows], dtype=bool).reshape(
        len(rows), len(events)
    )
    starts = np.array([e["seconds"] for e in events], dtype=float)
    ends = starts + np.array([max(e.get("duration") or 0.0, 0.0) for e in events], dtype=float)
    t = np.array([float(times[i]) for i in rows])[:, None]
    gaps = np.maximum.reduce([starts[None, :] - t, np.zeros((len(rows), len(events))), t - ends[None, :]]) if len(
        events) else np.zeros((len(rows), 0))
    cost = np.where(compat & (gaps <= tol), gaps, _INF)
    matched: dict[int, int] = {}
    if len(events):
        r_idx, c_idx = linear_sum_assignment(cost)
        for r, c in zip(r_idx, c_idx):
            if cost[r, c] < _INF:
                matched[r] = c
    for r, i in enumerate(rows):
        if r in matched:
            verdicts[i] = {"status": "supported", "event": int(matched[r]), "gap": round(float(gaps[r, matched[r]]), 2)}
            continue
        options = gaps[r][compat[r]] if len(events) else np.array([])
        if options.size == 0:
            verdicts[i] = {"status": "contradicted", "event": None, "gap": None}
        elif options.min() <= tol:
            verdicts[i] = {"status": "duplicate", "event": None, "gap": round(float(options.min()), 2)}
        else:
            verdicts[i] = {"status": "wrong_time", "event": None, "gap": round(float(options.min()), 2)}
    return verdicts


# ---------------------------------------------------------------- per-episode counts


def segment_events(events: list[dict], start: float, end: float) -> list[dict]:
    return [e for e in events if start <= e["seconds"] < end]


def _all_events(rec: dict, scale: str = "1.0") -> list[dict]:
    events = list(rec["events"])
    behaviors = rec.get("behaviors") or {}
    events += behaviors.get(scale, [])
    return sorted(events, key=lambda e: e["seconds"])


def _recall_pool(events: list[dict], with_behaviors: bool) -> list[int]:
    kinds = {k for t, ks in RECALL_KINDS.items() if with_behaviors or t not in BEHAVIOR_TYPES for k in ks}
    return [j for j, e in enumerate(events) if e["kind"] in kinds]


def _signature(claims: list[dict]) -> tuple:
    return tuple((c.get("type"), c.get("player"), c.get("text", "").strip().lower()) for c in claims)


def _alternates(claims: list[dict]) -> bool | None:
    named = [c["player"] for c in claims if c.get("player") in ("P1", "P2")]
    if len(named) < 4:
        return None
    return all(a != b for a, b in zip(named, named[1:]))


def episode_counts(rec: dict, condition: str, cap: int, draws: int = 10, seed: int = 0,
                   behavior_scale: str = "1.0") -> dict:
    """Every counter the v2 tables need, for one episode and one condition."""
    rng = random.Random(f"{seed}:{rec['trial_id']}:{condition}")
    block = rec["conditions"][condition]
    events_all = _all_events(rec, behavior_scale)
    with_behaviors = bool(rec.get("behaviors"))
    c: dict = defaultdict(float)
    lists: dict[str, list] = defaultdict(list)
    signatures = []

    for seg in block["segments"]:
        claims = seg["claims"]
        seg_ev = segment_events(events_all, seg["start"], seg["end"])
        verdicts = match_segment(claims, seg_ev)

        # precision side
        for claim, v in zip(claims, verdicts):
            c["claims"] += 1
            player = claim.get("player", "UNCLEAR")
            if v["status"] == "unchecked":
                c["unchecked"] += 1
                continue
            c["checkable"] += 1
            c[v["status"]] += 1
            ctype = claim.get("type")
            c[f"type_{ctype}_checkable"] += 1
            c[f"type_{ctype}_supported"] += v["status"] == "supported"
            if player in ("P1", "P2"):
                c["named_checkable"] += 1
                c["named_supported"] += v["status"] == "supported"
            else:
                c["unnamed_checkable"] += 1
                c["unnamed_supported"] += v["status"] == "supported"

        # recall side: which true events did some claim take
        pool = _recall_pool(seg_ev, with_behaviors)
        taken = {v["event"] for v in verdicts if v["status"] == "supported"}
        c["events"] += len(pool)
        c["events_recalled"] += sum(1 for j in pool if j in taken)
        c["events_ceiling"] += min(cap, len(pool))
        for ctype, kinds in RECALL_KINDS.items():
            idx = [j for j in pool if seg_ev[j]["kind"] in kinds]
            c[f"recall_{ctype}_events"] += len(idx)
            c[f"recall_{ctype}_hit"] += sum(1 for j in idx if j in taken)

        # pickup, scored the pilot's way (fill_dish counts)
        if any(cl.get("type") == "pickup" for cl in claims):
            alt = match_segment(claims, seg_ev, type_kinds=PICKUP_INCL_FILL)
            for cl, v in zip(claims, alt):
                if cl.get("type") == "pickup" and v["status"] != "unchecked":
                    c["pickup_fill_checkable"] += 1
                    c["pickup_fill_supported"] += v["status"] == "supported"

        # time error: nearest compatible event within 15 s
        for claim in claims:
            if not checkable(claim):
                continue
            gaps = [gap(e, claim["time"]) for e in seg_ev if compatible(claim, e)]
            if gaps and min(gaps) <= TIME_ERROR_WINDOW_S:
                lists["time_errors"].append(min(gaps))

        # actor: for named claims, the nearest same-kind event with any player
        for claim in claims:
            if not checkable(claim) or claim.get("player") not in ("P1", "P2") or claim.get("type") == "congestion":
                continue
            near = [(gap(e, claim["time"]), e) for e in seg_ev
                    if compatible(claim, e, ignore_player=True) and e["player"] is not None]
            near = [(g, e) for g, e in near if g <= CLAIM_TOLERANCE_S]
            if not near:
                continue
            _, event = min(near, key=lambda x: x[0])
            said = 0 if claim["player"] == "P1" else 1
            c["actor_checked"] += 1
            c["actor_correct"] += event["player"] == said
            c["actor_claim_p1"] += said == 0
            c["actor_event_p1"] += event["player"] == 0

        # tolerance curve and the random-time baseline at each tolerance
        n_check = sum(1 for cl in claims if checkable(cl))
        if n_check:
            for tol in TOLERANCES:
                vs = match_segment(claims, seg_ev, tol=tol)
                c[f"tol_{tol}_supported"] += sum(v["status"] == "supported" for v in vs)
                c[f"tol_{tol}_checkable"] += n_check
                for _ in range(draws):
                    times = [rng.uniform(seg["start"], seg["end"]) if cl.get("time") is not None else None
                             for cl in claims]
                    rv = match_segment(claims, seg_ev, tol=tol, times=times)
                    c[f"tol_{tol}_random_supported"] += sum(v["status"] == "supported" for v in rv) / draws

            # player swap: named claims re-checked with P1 and P2 swapped
            swapped = [dict(cl, player={"P1": "P2", "P2": "P1"}.get(cl.get("player"), cl.get("player")))
                       for cl in claims]
            sv = match_segment(swapped, seg_ev)
            for cl, v, s in zip(claims, verdicts, sv):
                if cl.get("player") in ("P1", "P2") and v["status"] != "unchecked":
                    c["swap_named"] += 1
                    c["swap_named_ok"] += v["status"] != "contradicted"
                    c["swap_swapped_ok"] += s["status"] != "contradicted"

            # clip-relative timestamps: would the claim be supported at time + start?
            for cl, v in zip(claims, verdicts):
                if v["status"] in ("unchecked", "supported"):
                    continue
                c["unsupported"] += 1
                c["before_window"] += cl["time"] < seg["start"]
                shifted = match_segment([cl], seg_ev, times=[cl["time"] + seg["start"]])[0]
                c["offset_rescued"] += shifted["status"] == "supported"

        # output collapse
        for cl in claims:
            if cl.get("time") is not None:
                c["timed"] += 1
                c["round5"] += float(cl["time"]) % 5 == 0
        signatures.append(_signature(claims))
        alt = _alternates(claims)
        if alt is not None:
            c["alternation_eligible"] += 1
            c["alternating"] += alt
        c["minutes"] += 1
        if seg.get("deliveries_claimed") is not None:
            claimed, true = seg["deliveries_claimed"], seg["deliveries_true"]
            c["delivery_answers"] += 1
            c["delivery_abs_err"] += abs(claimed - true)
            c["delivery_signed_err"] += claimed - true
            c["delivery_says_one"] += claimed == 1
            c["delivery_exact"] += claimed == true
            lists["delivery_pairs"].append((true, claimed))
        c["parse_failures"] += bool(seg.get("parse_failed"))

    sig_counts = Counter(s for s in signatures if s)
    c["minutes_repeated"] = sum(1 for s in signatures if s and sig_counts[s] > 1)
    return {"counts": dict(c), "lists": dict(lists)}


def entropy_bits(values: list[int]) -> float | None:
    if not values:
        return None
    counts = Counter(values)
    n = len(values)
    return -sum(k / n * math.log2(k / n) for k in counts.values())
