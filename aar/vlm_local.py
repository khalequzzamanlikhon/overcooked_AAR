"""Local Video-LLM backend (Qwen2.5-VL) so the whole pipeline runs on-box.

One model serves both jobs: video-in AAR generation and text-only AAR
generation from the telemetry timeline. Loading it once and reusing it is the
point -- a second model would double VRAM for no benefit.

VRAM, bf16, rough:
  Qwen2.5-VL-3B-Instruct   ~8 GB   fits almost anywhere
  Qwen2.5-VL-7B-Instruct   ~17 GB  needs a 24GB card, or shard across both
  Qwen2.5-VL-32B-Instruct  ~70 GB  needs both cards and then some

Video frames dominate activation memory, not the weights. If you OOM mid-run
it will be on a long clip, not at load -- drop `max_pixels` or raise
`RenderConfig.subsample` before reaching for a smaller model.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_model = None
_processor = None


def _resolve_device_map(device: str) -> str | dict:
    """`auto` shards across visible GPUs; `cuda:0`/`cuda:1` pins to one."""
    return "auto" if device == "auto" else {"": device}


def load_backend(model_id: str, device: str = "auto", max_pixels: int | None = None):
    """Load once per process. Returns (model, processor)."""
    global _model, _processor
    if _model is not None:
        return _model, _processor

    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    logger.info("loading %s onto %s", model_id, device)
    processor_kwargs = {}
    if max_pixels is not None:
        # caps per-frame visual tokens; the main OOM lever for video input
        processor_kwargs["max_pixels"] = max_pixels

    _processor = AutoProcessor.from_pretrained(model_id, **processor_kwargs)
    _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map=_resolve_device_map(device),
        attn_implementation="sdpa",
    )
    _model.eval()
    logger.info("model loaded")
    return _model, _processor


def _generate(messages: list[dict], max_new_tokens: int) -> str:
    import torch
    from qwen_vl_utils import process_vision_info

    model, processor = _model, _processor
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
    ).to(model.device)

    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]


def generate_text(prompt: str, max_new_tokens: int = 1200) -> str:
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return _generate(messages, max_new_tokens)


def generate_from_video(video_path: Path, prompt: str, fps: float = 2.0, max_new_tokens: int = 1200) -> str:
    """`fps` is the rate Qwen samples the clip at, independent of the mp4's own fps."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": f"file://{video_path.resolve()}", "fps": fps},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    return _generate(messages, max_new_tokens)
