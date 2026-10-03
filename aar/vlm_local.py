"""Local Qwen-VL backend, used for every condition in the study.

One model does all the jobs -- claims from an event log, claims from video,
answers to probe questions, and writing the review from claims -- because a
difference between two conditions should come from the input, not from two
different models.

Two model families are supported, picked from the model id:

  Qwen2.5-VL  the pilot model. Loaded in 4-bit NF4 (vision tower in bf16) or bf16.
  Qwen3-VL    puts text timestamps between video patches, so it is the direct
              test of whether the pilot's timing failure is a model limit.
              Its processor takes 16 px patches and per-video metadata.

Memory: this box shares its GPUs with other jobs. 4-bit goes on one card
(~6 GB); bf16 (~17 GB) is spread over every visible card with `device="auto"`.
Video frames, not weights, dominate what is left: a 60 s segment at 2 fps is
~10k visual tokens.
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
_family = None


def model_family(model_id: str) -> str:
    name = model_id.lower()
    if "qwen3-vl" in name:
        return "qwen3_vl"
    if "qwen2.5-vl" in name:
        return "qwen2_5_vl"
    raise ValueError(f"no backend for {model_id!r}: expected a Qwen2.5-VL or Qwen3-VL model")


def _max_memory(margin_gib: float = 2.0) -> dict:
    """What each visible GPU has free right now, minus a margin for activations."""
    import torch

    out = {}
    for i in range(torch.cuda.device_count()):
        free, _ = torch.cuda.mem_get_info(i)
        out[i] = f"{max(free / 2**30 - margin_gib, 1):.0f}GiB"
    return out


def load_backend(model_id: str, device: str = "cuda:0", load_in_4bit: bool = True):
    global _model, _processor, _model_id, _family
    if _model is not None:
        return _model, _processor

    import torch
    import transformers
    from transformers import AutoProcessor, BitsAndBytesConfig

    family = model_family(model_id)
    logger.info("loading %s (%s) onto %s (4bit=%s)", model_id, family, device, load_in_4bit)
    kwargs: dict = {"dtype": torch.bfloat16, "attn_implementation": "sdpa"}
    if device == "auto":
        kwargs["device_map"] = "auto"
        kwargs["max_memory"] = _max_memory()
        logger.info("max_memory per GPU: %s", kwargs["max_memory"])
    else:
        kwargs["device_map"] = {"": device}
    if load_in_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            # keep the vision encoder and the output head in bf16
            llm_int8_skip_modules=["visual", "lm_head"],
        )

    cls = {
        "qwen2_5_vl": transformers.Qwen2_5_VLForConditionalGeneration,
        "qwen3_vl": getattr(transformers, "Qwen3VLForConditionalGeneration", None),
    }[family]
    if cls is None:
        raise RuntimeError(f"transformers {transformers.__version__} has no Qwen3-VL; need >= 4.57")

    _processor = AutoProcessor.from_pretrained(model_id)
    _model = cls.from_pretrained(model_id, **kwargs)
    _model.eval()
    _model_id, _family = model_id, family
    logger.info("model loaded")
    return _model, _processor


def model_name() -> str:
    return _model_id or "not loaded"


def model_revision() -> str | None:
    """The commit hash of the loaded weights, for config.json."""
    return getattr(getattr(_model, "config", None), "_commit_hash", None)


def _inputs(messages: list[dict]):
    from qwen_vl_utils import process_vision_info

    processor = _processor
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if _family == "qwen3_vl":
        images, videos, video_kwargs = process_vision_info(
            messages, image_patch_size=16, return_video_kwargs=True, return_video_metadata=True
        )
        metadata = None
        if videos is not None:
            videos, metadata = map(list, zip(*videos))
        return processor(
            text=[text], images=images, videos=videos, video_metadata=metadata, do_resize=False,
            padding=True, return_tensors="pt", **video_kwargs,
        )
    images, videos, video_kwargs = process_vision_info(messages, return_video_kwargs=True)
    return processor(text=[text], images=images, videos=videos, padding=True, return_tensors="pt", **video_kwargs)


def _generate(messages: list[dict], max_new_tokens: int, do_sample: bool = False, seed: int = 0) -> str:
    import torch

    model, processor = _model, _processor
    inputs = _inputs(messages).to(model.device)
    gen: dict = {"max_new_tokens": max_new_tokens, "do_sample": do_sample}
    if do_sample:
        torch.manual_seed(seed)
        gen.update(temperature=0.7, top_p=0.9)
    else:
        gen.update(temperature=None, top_p=None, top_k=None)
    with torch.inference_mode():
        generated = model.generate(**inputs, **gen)
    trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]


def _video_part(video_path: Path, fps: float) -> dict:
    return {"type": "video", "video": f"file://{Path(video_path).resolve()}", "fps": fps}


def generate_text(prompt: str, max_new_tokens: int = 800, do_sample: bool = False, seed: int = 0) -> str:
    return _generate([{"role": "user", "content": [{"type": "text", "text": prompt}]}], max_new_tokens, do_sample, seed)


def generate_from_video(video_path: Path, prompt: str, fps: float, max_new_tokens: int = 800,
                        do_sample: bool = False, seed: int = 0) -> str:
    """`fps` is how often the model is given a frame, independent of the mp4."""
    messages = [{"role": "user", "content": [_video_part(video_path, fps), {"type": "text", "text": prompt}]}]
    return _generate(messages, max_new_tokens, do_sample, seed)


def generate_from_image(image_path: Path, prompt: str, max_new_tokens: int = 32) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": f"file://{Path(image_path).resolve()}"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    return _generate(messages, max_new_tokens)


_JSON_BLOCK = re.compile(r"[\[{].*[\]}]", re.S)
_FLAT_OBJECT = re.compile(r"\{[^{}]*\}")
_DELIVERIES = re.compile(r'"deliveries"\s*:\s*(\d+)')


def _salvage(text: str) -> dict | None:
    """Output cut off at the token limit (Qwen3-VL ignores the claim cap and
    keeps listing): keep every claim object that was written out in full."""
    claims = [c for c in (_loads(m.group(0)) for m in _FLAT_OBJECT.finditer(text)) if isinstance(c, dict) and "text" in c]
    deliveries = _DELIVERIES.search(text)
    if not claims and not deliveries:
        return None
    return {"deliveries": int(deliveries.group(1)) if deliveries else None, "claims": claims, "truncated": True}


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
        return _salvage(text)
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
