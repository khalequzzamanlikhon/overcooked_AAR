"""Local Qwen2.5-VL backend, used for every condition in the study.

One model does all three jobs -- claims from an event log, claims from video,
and writing the review from claims -- because a difference between two
conditions should come from the input, not from two different models.

Memory: this box shares its GPUs with other jobs, so the 7B is loaded in 4-bit
NF4 with the vision tower left in bf16 (~6 GB instead of ~17 GB). Video frames,
not weights, dominate what is left: a 60 s segment at 2 fps is ~10k visual
tokens, a whole 180 s episode would be ~30k.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_model = None
_processor = None
_model_id = None


def load_backend(model_id: str, device: str = "cuda:0", load_in_4bit: bool = True):
    global _model, _processor, _model_id
    if _model is not None:
        return _model, _processor

    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2_5_VLForConditionalGeneration

    logger.info("loading %s onto %s (4bit=%s)", model_id, device, load_in_4bit)
    kwargs: dict = {"dtype": torch.bfloat16, "attn_implementation": "sdpa", "device_map": {"": device}}
    if load_in_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            # keep the vision encoder and the output head in bf16
            llm_int8_skip_modules=["visual", "lm_head"],
        )

    _processor = AutoProcessor.from_pretrained(model_id)
    _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id, **kwargs)
    _model.eval()
    _model_id = model_id
    logger.info("model loaded")
    return _model, _processor


def model_name() -> str:
    return _model_id or "not loaded"


def _generate(messages: list[dict], max_new_tokens: int) -> str:
    import torch
    from qwen_vl_utils import process_vision_info

    model, processor = _model, _processor
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos, video_kwargs = process_vision_info(messages, return_video_kwargs=True)
    inputs = processor(
        text=[text], images=images, videos=videos, padding=True, return_tensors="pt", **video_kwargs
    ).to(model.device)

    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]


def generate_text(prompt: str, max_new_tokens: int = 800) -> str:
    return _generate([{"role": "user", "content": [{"type": "text", "text": prompt}]}], max_new_tokens)


def generate_from_video(video_path: Path, prompt: str, fps: float, max_new_tokens: int = 800) -> str:
    """`fps` is how often the model is given a frame, independent of the mp4."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": f"file://{Path(video_path).resolve()}", "fps": fps},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    return _generate(messages, max_new_tokens)


_JSON_BLOCK = re.compile(r"[\[{].*[\]}]", re.S)


def _loads(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:  # trailing commas are the usual breakage
            return json.loads(re.sub(r",(\s*[}\]])", r"\1", text))
        except json.JSONDecodeError:
            return None


def parse_json(raw: str) -> dict | None:
    """Models wrap JSON in prose or code fences, and sometimes return a list of
    one-key objects instead of the object asked for. Both are recoverable."""
    text = re.sub(r"```(?:json)?", "", raw).strip()
    parsed = _loads(text)
    if parsed is None:
        match = _JSON_BLOCK.search(text)
        parsed = _loads(match.group(0)) if match else None
    if parsed is None:
        return None
    if isinstance(parsed, dict) and ("claims" in parsed or "deliveries" in parsed):
        return parsed
    # flatten [{"deliveries": n}, {"claim": {...}}, {...}]
    items = parsed if isinstance(parsed, list) else [parsed]
    out: dict = {"deliveries": None, "claims": []}
    for item in items:
        if not isinstance(item, dict):
            continue
        if "deliveries" in item and not isinstance(item.get("deliveries"), list):
            out["deliveries"] = item["deliveries"]
        inner = item.get("claim") if isinstance(item.get("claim"), dict) else item
        if isinstance(inner, dict) and "text" in inner:
            out["claims"].append(inner)
        for claim in item.get("claims", []) if isinstance(item.get("claims"), list) else []:
            if isinstance(claim, dict):
                out["claims"].append(claim)
    return out if out["claims"] or out["deliveries"] is not None else None
