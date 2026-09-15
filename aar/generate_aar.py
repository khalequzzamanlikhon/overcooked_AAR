"""Generate after-action reviews from telemetry text and from video.

The comparison between the two is the research content. Telemetry knows
exactly what happened but not what it looked like; video sees hesitation,
near-misses, and repeated blocked attempts that never become discrete logged
events. Where they disagree is the interesting part.

Backend is chosen by `LLMConfig.backend`:
  'local' -> Qwen2.5-VL on your GPUs, no API keys, nothing leaves the box
  'api'   -> Groq for text, Gemini for video
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .config import LLMConfig

logger = logging.getLogger(__name__)

_AAR_INSTRUCTION = """You are writing an after-action review for a two-person
cooperative cooking task (Overcooked). Two players share a kitchen and must
deliver onion soups as fast as possible.

Write a short AAR covering:
1. What the team did well.
2. What caused delays or wasted effort.
3. One specific, concrete thing they should do differently next time.

Be specific and evidence-based. If you are not sure something happened, say so
rather than asserting it. Do not speculate about intent you cannot observe."""

_COMPARE_INSTRUCTION = """Below are two after-action reviews of the SAME
episode. One was written from a structured event log, the other from watching
the gameplay video.

Identify:
1. Claims both agree on.
2. Claims only one makes.
3. Any place they directly contradict each other.

For each disagreement, state which source would be more reliable for that
specific kind of claim, and why."""


def init_backend(cfg: LLMConfig) -> None:
    """Load the local model once up front, so the cost isn't paid mid-loop."""
    if cfg.backend == "local":
        from .vlm_local import load_backend

        load_backend(cfg.local_model_id, cfg.device, cfg.max_pixels)


def _api_text(prompt: str, cfg: LLMConfig) -> str:
    import groq

    client = groq.Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=cfg.api_text_model, max_tokens=cfg.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _api_video(video_path: Path, prompt: str, cfg: LLMConfig) -> str:
    # Small clips (a few hundred KB, well under the 20MB inline request cap) go
    # straight in the request body -- skips the separate Files-API upload/poll
    # step entirely, which some API-key setups can't reach.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    video_part = types.Part.from_bytes(data=video_path.read_bytes(), mime_type="video/mp4")
    response = client.models.generate_content(model=cfg.api_video_model, contents=[video_part, prompt])
    return response.text


def aar_from_telemetry(timeline: str, cfg: LLMConfig) -> str:
    prompt = f"{_AAR_INSTRUCTION}\n\n{timeline}"
    if cfg.backend == "local":
        from .vlm_local import generate_text

        return generate_text(prompt, cfg.max_tokens)
    return _api_text(prompt, cfg)


def aar_from_video(video_path: Path, cfg: LLMConfig) -> str:
    """Video only -- no timeline given, the model must read the gameplay."""
    if cfg.backend == "local":
        from .vlm_local import generate_from_video

        return generate_from_video(video_path, _AAR_INSTRUCTION, cfg.video_sample_fps, cfg.max_tokens)
    return _api_video(video_path, _AAR_INSTRUCTION, cfg)


def compare_aars(telemetry_aar: str, video_aar: str, cfg: LLMConfig) -> str:
    prompt = (
        f"{_COMPARE_INSTRUCTION}\n\n"
        f"=== AAR A (from event log) ===\n{telemetry_aar}\n\n"
        f"=== AAR B (from video) ===\n{video_aar}"
    )
    if cfg.backend == "local":
        from .vlm_local import generate_text

        return generate_text(prompt, cfg.max_tokens)
    return _api_text(prompt, cfg)
