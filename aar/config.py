"""Config for the Overcooked after-action-review pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LAYOUTS: tuple[str, ...] = (
    "cramped_room",
    "asymmetric_advantages",
    "coordination_ring",
    "random0",
    "random3",
)


@dataclass(frozen=True)
class DataConfig:
    train_pickle_name: str = "clean_train_trials.pickle"
    test_pickle_name: str = "clean_test_trials.pickle"
    out_dir: Path = Path("out")


@dataclass(frozen=True)
class RenderConfig:
    fps: int = 10
    subsample: int = 4  # render every Nth timestep; 1204/4 ~= 300 frames
    max_frames: int = 400


@dataclass(frozen=True)
class LLMConfig:
    """`backend='local'` runs Qwen2.5-VL on your own GPUs, no API keys.

    `device`: 'auto' shards across every visible GPU; 'cuda:0' or 'cuda:1'
    pins to one card. Pin when you're sharing the box -- 'auto' will happily
    claim both.
    """

    backend: str = "local"  # 'local' | 'api'
    local_model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    device: str = "auto"
    max_pixels: int = 401408  # 512*28*28; lower this first if you OOM on video
    video_sample_fps: float = 2.0
    max_tokens: int = 1200

    # only used when backend='api'
    api_text_model: str = "openai/gpt-oss-120b"
    api_video_model: str = "gemini-3.6-flash"
