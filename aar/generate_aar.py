"""Ask the model what happened, then ask it to write the review.

Both conditions run the same two stages with the same wording:

  stage 1  source (event log text | gameplay video) -> numbered claims, as JSON
  stage 2  claims -> after-action review, text only

Splitting it this way is what makes the comparison checkable: a claim carries a
time, a player and a type, so it can be checked against the log one by one. A
paragraph of prose cannot.
"""
from __future__ import annotations

import logging

from .config import LLMConfig
from .vlm_local import generate_from_video, generate_text, parse_json

logger = logging.getLogger(__name__)

# Identical for both conditions. Only the SOURCE line differs.
_RULES = """Two players cook onion soups together in a kitchen (the game
Overcooked). A soup needs 3 onions in a pot; it cooks for about 20 seconds;
someone then picks it up with a clean dish and takes it to the serving hatch.

P1 is the player in the blue hat, labelled P1 on screen.
P2 is the player in the green hat, labelled P2 on screen."""

_CLAIMS_TASK = """List what you can tell happened between {start:.0f} s and {end:.0f} s.
Use the episode clock (the times in the source), not time since the clip started.

Answer with ONE JSON object and nothing else:
{{"deliveries": <how many soups were delivered in this minute>,
  "claims": [{{"time": <seconds>, "player": "P1" | "P2" | "both" | "unclear",
              "type": "delivery" | "pickup" | "pot" | "counter" | "blocked" | "idle" | "coordination" | "strategy" | "other",
              "text": "<one short sentence>"}}]}}

At most 8 claims, most important first. Only state what the source supports.
Use "both" when they both did it and "unclear" when you cannot tell who did it.
Do not guess at intentions."""

_AAR_TASK = """Here is what was observed across a 180 second episode of a
two-player cooking game, as claims with timestamps.

{claims}

Final score: {score}. Layout: {layout}.

Write a short after-action review for the two players:
1. What the team did well.
2. What cost them time.
3. One concrete thing to do differently next time.

Use only the claims above. Refer to times and players. If the claims do not
support something, do not say it. Six sentences at most."""


def init_backend(cfg: LLMConfig) -> None:
    from .vlm_local import load_backend

    load_backend(cfg.model_id, cfg.device, cfg.load_in_4bit)


def _claims_prompt(start: float, end: float, source: str | None) -> str:
    task = _CLAIMS_TASK.format(start=start, end=end)
    if source is None:
        return f"{_RULES}\n\nSOURCE: the video above, which covers seconds {start:.0f}-{end:.0f} of the episode.\n\n{task}"
    return f"{_RULES}\n\nSOURCE: an event log of the episode.\n\n{source}\n\n{task}"


def _normalise(parsed: dict | None, raw: str) -> dict:
    if not isinstance(parsed, dict):
        return {"deliveries": None, "claims": [], "parse_failed": True, "raw": raw}
    claims = parsed.get("claims") or []
    clean = []
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict) or "text" not in claim:
            continue
        try:
            time_s = float(claim.get("time"))
        except (TypeError, ValueError):
            time_s = None
        player = str(claim.get("player", "unclear")).upper().replace("PLAYER ", "P")
        clean.append(
            {
                "time": time_s,
                "player": player if player in {"P1", "P2", "BOTH", "UNCLEAR"} else "UNCLEAR",
                "type": str(claim.get("type", "other")).lower(),
                "text": str(claim["text"]).strip(),
            }
        )
    deliveries = parsed.get("deliveries")
    try:
        deliveries = int(deliveries)
    except (TypeError, ValueError):
        deliveries = None
    return {"deliveries": deliveries, "claims": clean, "parse_failed": False}


_RETRY = '\n\nReturn ONE JSON object starting with {"deliveries": and nothing else.'


def claims_from_timeline(timeline: str, start: float, end: float, cfg: LLMConfig) -> dict:
    prompt = _claims_prompt(start, end, timeline)
    got = _normalise(parse_json(raw := generate_text(prompt, cfg.max_new_tokens)), raw)
    if got.get("parse_failed"):
        got = _normalise(parse_json(raw := generate_text(prompt + _RETRY, cfg.max_new_tokens)), raw)
        got["retried"] = True
    return got


def claims_from_video(video_path, start: float, end: float, fps: float, cfg: LLMConfig) -> dict:
    prompt = _claims_prompt(start, end, None)
    raw = generate_from_video(video_path, prompt, fps, cfg.max_new_tokens)
    got = _normalise(parse_json(raw), raw)
    if got.get("parse_failed"):
        raw = generate_from_video(video_path, prompt + _RETRY, fps, cfg.max_new_tokens)
        got = _normalise(parse_json(raw), raw)
        got["retried"] = True
    return got


def aar_from_claims(claims: list[dict], layout: str, score: float, cfg: LLMConfig) -> str:
    if not claims:
        return "(no claims were produced for this episode)"
    lines = [f"- t={c['time']}s {c['player']}: {c['text']}" if c["time"] is not None else f"- {c['player']}: {c['text']}" for c in claims]
    prompt = _AAR_TASK.format(claims="\n".join(lines), score=int(score), layout=layout)
    return generate_text(prompt, cfg.max_new_tokens).strip()
