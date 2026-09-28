"""Every prompt the study sends, in one place, with a version id.

The version id is a hash of the prompt text, written into each run's
config.json, so a number in a table can always be traced to the exact wording
that produced it.

Stage 1 (claims) is the same for every condition except the SOURCE block.
Stage 2 (the review) is the same for every condition, the oracle included.
"""
from __future__ import annotations

import hashlib

RULES = """Two players cook onion soups together in a kitchen (the game
Overcooked). A soup needs 3 onions in a pot; it cooks for about 20 seconds;
someone then picks it up with a clean dish and takes it to the serving hatch.

P1 is the player in the blue hat, labelled P1 on screen.
P2 is the player in the green hat, labelled P2 on screen."""

CLAIM_TYPES = (
    "delivery", "pickup", "pot", "counter", "blocked", "idle",
    "waiting", "handoff", "congestion",
    "coordination", "strategy", "other",
)

CLAIMS_TASK = """List what you can tell happened between {start:.0f} s and {end:.0f} s.
Use the episode clock (the times in the source), not time since the clip started.

Answer with ONE JSON object and nothing else:
{{"deliveries": <how many soups were delivered in this minute>,
  "claims": [{{"time": <seconds>, "player": "P1" | "P2" | "both" | "unclear",
              "type": "delivery" | "pickup" | "pot" | "counter" | "blocked" | "idle" | "waiting" | "handoff" | "congestion" | "coordination" | "strategy" | "other",
              "text": "<one short sentence>"}}]}}

Types: pickup = took an item from a dispenser or counter; pot = put an onion in
a pot or took soup out of it; counter = put an item down; blocked = walked into
the other player; idle = stood still; waiting = stood by a cooking pot;
handoff = one player put an item down and the other picked it up;
congestion = both players crowded around the same station.

At most {cap} claims, most important first. Only state what the source supports.
Use "both" when they both did it and "unclear" when you cannot tell who did it.
Do not guess at intentions."""

SOURCE_VIDEO = (
    "SOURCE: the video above, which covers seconds {start:.0f}-{end:.0f} of the episode. "
    "The episode clock is shown at the top of every frame."
)
SOURCE_LOG = "SOURCE: an event log of the episode.\n\n{log}"
SOURCE_VIDEO_LOG = (
    "SOURCE: the video above, which covers seconds {start:.0f}-{end:.0f} of the episode "
    "(the episode clock is shown at the top of every frame), and an event log of the same seconds.\n\n{log}"
)
SOURCE_STATE = (
    "SOURCE: the game state twice per second, as text: where each player stands, which way "
    "they face, what they hold, and what is in each pot.\n\n{state}"
)
SOURCE_BLIND = (
    "SOURCE: none. You are not shown this episode. It was played on the {layout} layout. "
    "Say what most likely happened in these seconds."
)

AAR_TASK = """Here is what was observed across a 180 second episode of a
two-player cooking game, as claims with timestamps.

{claims}

Final score: {score}. Layout: {layout}.

Write a short after-action review for the two players:
1. What the team did well.
2. What cost them time.
3. One concrete thing to do differently next time.

Use only the claims above. Refer to times and players. If the claims do not
support something, do not say it. Six sentences at most."""

RETRY = '\n\nReturn ONE JSON object starting with {"deliveries": and nothing else.'

# Perception probe: one short question per item, one short answer.
PROBE_PREAMBLE = RULES + "\n\n"
PROBE_SOURCE_VIDEO = "Look at the {what} above."
PROBE_SOURCE_TEXT = "Here is a description of the game {what}:\n\n{text}"
PROBE_ANSWER = "Answer with {fmt} only, nothing else."


def claims_prompt(condition: str, start: float, end: float, cap: int, *, log: str = "", state: str = "",
                  layout: str = "") -> str:
    task = CLAIMS_TASK.format(start=start, end=end, cap=cap)
    source = {
        "telemetry": lambda: SOURCE_LOG.format(log=log),
        "video_dense": lambda: SOURCE_VIDEO.format(start=start, end=end),
        "video_sparse": lambda: SOURCE_VIDEO.format(start=start, end=end),
        "video_log": lambda: SOURCE_VIDEO_LOG.format(start=start, end=end, log=log),
        "state_text": lambda: SOURCE_STATE.format(state=state),
        "blind": lambda: SOURCE_BLIND.format(layout=layout),
    }[condition]()
    return f"{RULES}\n\n{source}\n\n{task}"


def aar_prompt(claim_lines: str, score: float, layout: str) -> str:
    return AAR_TASK.format(claims=claim_lines, score=int(score), layout=layout)


def prompt_version() -> str:
    """A short hash of every prompt string above."""
    text = "\x00".join(
        [RULES, CLAIMS_TASK, SOURCE_VIDEO, SOURCE_LOG, SOURCE_VIDEO_LOG, SOURCE_STATE, SOURCE_BLIND, AAR_TASK, RETRY,
         PROBE_PREAMBLE, PROBE_SOURCE_VIDEO, PROBE_SOURCE_TEXT, PROBE_ANSWER]
    )
    return hashlib.sha256(text.encode()).hexdigest()[:12]
