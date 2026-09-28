"""Ask the model what happened, then ask it to write the review.

Every condition runs the same two stages with the same wording:

  stage 1  source (event log | video | video + log | raw state | nothing) -> numbered claims, as JSON
  stage 2  claims -> after-action review, text only

Splitting it this way is what makes the comparison checkable: a claim carries a
time, a player and a type, so it can be checked against the log one by one. A
paragraph of prose cannot. The prompts themselves live in `prompts.py`.
"""
from __future__ import annotations

import logging
from pathlib import Path

from . import prompts
from .config import CLAIM_CAP, LLMConfig
from .vlm_local import generate_from_video, generate_text, parse_json

logger = logging.getLogger(__name__)

VIDEO_CONDITIONS = {"video_dense", "video_sparse", "video_log"}


def init_backend(cfg: LLMConfig) -> None:
    from .vlm_local import load_backend

    load_backend(cfg.model_id, cfg.device, cfg.load_in_4bit)


def _normalise(parsed: dict | None, raw: str, cap: int = CLAIM_CAP) -> dict:
    """Clean claims, at most `cap` of them: a model that ignores the cap would
    otherwise get more chances to hit an event than one that obeys it."""
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
    return {"deliveries": deliveries, "claims": clean[:cap], "claims_over_cap": max(len(clean) - cap, 0),
            "truncated": bool(parsed.get("truncated")), "parse_failed": False, "raw": raw}


def claims_for_condition(
    condition: str,
    start: float,
    end: float,
    cfg: LLMConfig,
    *,
    log: str = "",
    state: str = "",
    layout: str = "",
    video: Path | None = None,
    fps: float = 2.0,
    cap: int = CLAIM_CAP,
) -> dict:
    """Stage 1 for one minute of one condition. Retries once if the JSON is unreadable."""
    prompt = prompts.claims_prompt(condition, start, end, cap, log=log, state=state, layout=layout)

    def ask(text: str) -> str:
        if condition in VIDEO_CONDITIONS:
            return generate_from_video(video, text, fps, cfg.max_new_tokens, cfg.do_sample, cfg.seed)
        return generate_text(text, cfg.max_new_tokens, cfg.do_sample, cfg.seed)

    got = _normalise(parse_json(raw := ask(prompt)), raw, cap)
    if got.get("parse_failed"):
        got = _normalise(parse_json(raw := ask(prompt + prompts.RETRY)), raw, cap)
        got["retried"] = True
    return got


def claim_lines(claims: list[dict]) -> str:
    return "\n".join(
        f"- t={c['time']}s {c['player']}: {c['text']}" if c.get("time") is not None else f"- {c['player']}: {c['text']}"
        for c in claims
    )


def aar_from_claims(claims: list[dict], layout: str, score: float, cfg: LLMConfig) -> str:
    if not claims:
        return "(no claims were produced for this episode)"
    prompt = prompts.aar_prompt(claim_lines(claims), score, layout)
    return generate_text(prompt, cfg.max_new_tokens, cfg.do_sample, cfg.seed).strip()


# event kind -> claim type, for the oracle's claims
_ORACLE_TYPE = {
    "delivery": "delivery", "pickup": "pickup", "place_pot": "pot", "fill_dish": "pot",
    "place_counter": "counter", "blocked": "blocked", "idle": "idle",
    "waiting": "waiting", "handoff": "handoff", "congestion": "congestion",
}


def oracle_claims(events: list[dict]) -> list[dict]:
    """The true events, written as the claims a perfect stage 1 would make."""
    out = []
    for e in events:
        kind = e["kind"]
        if kind not in _ORACLE_TYPE:
            continue
        player = "UNCLEAR" if e["player"] is None else f"P{e['player'] + 1}"
        if kind in ("handoff", "congestion"):
            player = "BOTH"
        out.append({"time": round(e["seconds"], 1), "player": player, "type": _ORACLE_TYPE[kind],
                    "text": e["text"].rstrip(".")})
    return out
