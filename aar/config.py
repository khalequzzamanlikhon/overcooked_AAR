"""Config for the Overcooked after-action-review comparison."""
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

# One episode is 180 s. Both sources are read one minute at a time so that the
# video condition fits in the model's context at 2 fps and both conditions get
# the same number of chances to make a claim.
SEGMENT_SECONDS: float = 60.0

# A claim about an event counts as matching a logged event if it lands within
# this many seconds of it. 3 s is about one pick-up-and-place cycle.
CLAIM_TOLERANCE_S: float = 3.0


@dataclass(frozen=True)
class DataConfig:
    train_pickle_name: str = "clean_train_trials.pickle"
    test_pickle_name: str = "clean_test_trials.pickle"
    out_dir: Path = Path("results/run")


@dataclass(frozen=True)
class RenderConfig:
    """Real time, not sped up: the mp4 is as long as the episode was."""

    tile_size: int = 75
    subsample: int = 1  # keep every timestep; the data is only ~6.7 Hz
    label_players: bool = True  # draw P1/P2 over the chefs
    segment_seconds: float = SEGMENT_SECONDS


@dataclass(frozen=True)
class LLMConfig:
    model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    device: str = "cuda:0"  # index within CUDA_VISIBLE_DEVICES
    load_in_4bit: bool = True  # 7B in bf16 does not fit next to other jobs here
    max_new_tokens: int = 800


# The two video conditions differ only in how often the model gets to see a
# frame. dense = 2 frames per real second; sparse = 1 frame per 3 real seconds,
# which is what a 6x-speed render sampled at 2 fps would have given.
VIDEO_FPS_DENSE: float = 2.0
VIDEO_FPS_SPARSE: float = 1.0 / 3.0

CONDITIONS: tuple[str, ...] = ("telemetry", "video_dense", "video_sparse")
