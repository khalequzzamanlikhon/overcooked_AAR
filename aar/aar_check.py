"""Fact-check the written review (stage 2), not just the claims (stage 1).

Stage 2 can add mistakes of its own: in the pilot, one review built from the
log said P1 made 24 deliveries when the team made 17. This pulls the two kinds
of checkable statement out of a review with regular expressions and checks
them against the log:

  counts         "17 deliveries", "delivered 5 soups": the number must be the
                 team's total or one player's total
  timed events   a sentence with a time ("t=42s", "at 42 seconds") and an event
                 word ("delivered", "picked up", ...): checked like a claim,
                 against the whole episode, with the usual 3 s tolerance

It is deliberately narrow: a statement it cannot parse is left alone, so the
error rate is over the statements it could check. The `oracle` condition's
reviews are written from the true events, so their error rate is stage 2's
own.
"""
from __future__ import annotations

import re

from .metrics import match_segment

_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
_NUM = r"(\d+|" + "|".join(_WORDS) + r")"
_COUNT_PATTERNS = [
    re.compile(r"\b" + _NUM + r"\s+(?:\w+\s+)?(?:soups?|deliveries|dishes|orders)\b", re.I),
    re.compile(r"deliver(?:ed|ing|s)?\s+(?:a\s+total\s+of\s+|only\s+|just\s+)?" + _NUM + r"\b(?!\s*(?:s\b|sec))", re.I),
]
_TIME = re.compile(
    r"t\s*=\s*(\d+(?:\.\d+)?)\s*s?\b|(?:at|around|by|near)\s+(?:t\s*=\s*)?(\d+(?:\.\d+)?)\s*(?:s\b|sec\b|seconds\b)", re.I
)
_PLAYER = re.compile(r"\b(?:P|Player\s*)([12])\b", re.I)
_EVENT_WORDS = [
    ("delivery", re.compile(r"deliver", re.I)),
    ("handoff", re.compile(r"hand(?:ed|off|s)|passed", re.I)),
    ("waiting", re.compile(r"wait", re.I)),
    ("blocked", re.compile(r"block|collid|bump", re.I)),
    ("idle", re.compile(r"idle|stood still|standing still", re.I)),
    ("pot", re.compile(r"(?:put|placed|added|dropped).{0,20}\bpot\b|\bpot\b.{0,20}(?:put|placed|added)", re.I)),
    ("counter", re.compile(r"(?:put|placed|left|set).{0,25}counter", re.I)),
    ("pickup", re.compile(r"pick(?:ed|s|ing)?\s+up|grab|took|collect", re.I)),
]


def _to_int(token: str) -> int:
    return int(token) if token.isdigit() else _WORDS[token.lower()]


def count_statements(text: str) -> list[int]:
    """"delivered two soups" matches both patterns; keep one per stretch of text."""
    spans = sorted((m.start(), m.end(), _to_int(m.group(1))) for p in _COUNT_PATTERNS for m in p.finditer(text))
    found, last_end = [], -1
    for start, end, value in spans:
        if start >= last_end:
            found.append(value)
            last_end = end
    return found


def timed_statements(text: str) -> list[dict]:
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        kind = next((k for k, pat in _EVENT_WORDS if pat.search(sentence)), None)
        if kind is None:
            continue
        players = {m.group(1) for m in _PLAYER.finditer(sentence)}
        player = f"P{players.pop()}" if len(players) == 1 else "UNCLEAR"
        for m in _TIME.finditer(sentence):
            out.append({"time": float(m.group(1) or m.group(2)), "player": player, "type": kind, "text": sentence})
    return out


def check_review(text: str, events: list[dict]) -> dict:
    deliveries = [e for e in events if e["kind"] == "delivery"]
    allowed = {len(deliveries), sum(e["player"] == 0 for e in deliveries), sum(e["player"] == 1 for e in deliveries)}
    counts = count_statements(text)
    count_errors = [n for n in counts if n not in allowed]
    claims = timed_statements(text)
    verdicts = match_segment(claims, events) if claims else []
    checked = [v for v in verdicts if v["status"] != "unchecked"]
    wrong = [c | {"status": v["status"]} for c, v in zip(claims, verdicts) if v["status"] in ("wrong_time", "contradicted")]  # a review may mention one event twice
    return {
        "count_statements": len(counts),
        "count_errors": len(count_errors),
        "count_error_values": count_errors,
        "timed_statements": len(checked),
        "timed_errors": len(wrong),
        "errors": wrong[:10],
    }
