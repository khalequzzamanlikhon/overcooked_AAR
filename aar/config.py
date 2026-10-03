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

# How many claims the model may make per minute. The pilot used 8, which caps
# recall far below the number of events in a busy minute; study v2 uses 20.
CLAIM_CAP_PILOT: int = 8
CLAIM_CAP: int = 20


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
    clock_strip_px: int = 48  # clock and score strip above the grid, in place of the package HUD
    segment_seconds: float = SEGMENT_SECONDS
    hud: str = "full"  # full = clock + score | clock = clock only | none = no strip (probe ablations)


@dataclass(frozen=True)
class LLMConfig:
    model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    device: str = "cuda:0"  # index within CUDA_VISIBLE_DEVICES, or "auto" to spread over all visible GPUs
    load_in_4bit: bool = True  # 7B in bf16 does not fit next to other jobs on one card here
    # 20 claims of JSON are ~800 tokens. More only lets a model that ignores the
    # cap (Qwen3-VL) keep listing; the claims past 20 are dropped anyway.
    max_new_tokens: int = 1100
    do_sample: bool = False  # greedy everywhere except the variance repeat
    seed: int = 0


# The two video conditions differ only in how often the model gets to see a
# frame. dense = 2 frames per real second; sparse = 1 frame per 3 real seconds,
# which is what a 6x-speed render sampled at 2 fps would have given.
VIDEO_FPS_DENSE: float = 2.0
VIDEO_FPS_SPARSE: float = 1.0 / 3.0

# The pilot's three conditions.
PILOT_CONDITIONS: tuple[str, ...] = ("telemetry", "video_dense", "video_sparse")

# Study v2. Every condition runs the same two stages with the same wording;
# only the SOURCE block of stage 1 changes. `oracle` skips stage 1 and writes
# the review from the true events, so a bad review can be blamed on stage 1 or
# stage 2.
CONDITIONS: tuple[str, ...] = (
    "blind",  # no source: what the model claims from its priors alone
    "telemetry",  # the event log
    "video_dense",  # video, 2 fps
    "video_sparse",  # video, 1 frame / 3 s
    "video_log",  # video and the event log together
    "state_text",  # raw per-step state as text, 2 Hz, no event abstraction
    "oracle",  # stage 2 only, from the true events
)

# The models in study v2: short tag -> (model id, 4-bit?)
MODELS: dict[str, tuple[str, bool]] = {
    "qwen25vl7b_4bit": ("Qwen/Qwen2.5-VL-7B-Instruct", True),
    "qwen25vl7b_bf16": ("Qwen/Qwen2.5-VL-7B-Instruct", False),
    "qwen3vl8b_bf16": ("Qwen/Qwen3-VL-8B-Instruct", False),
}
