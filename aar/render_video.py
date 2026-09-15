"""Render a Trial's trajectory into an mp4 -- this is how you get the video
modality without recording anyone playing.

Headless note: pygame needs a video driver. Set SDL_VIDEODRIVER=dummy (done
automatically below) or rendering fails on a server with no display.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pygame  # noqa: E402
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld  # noqa: E402
from overcooked_ai_py.visualization.state_visualizer import StateVisualizer  # noqa: E402

from .config import RenderConfig  # noqa: E402
from .data_loader import Trial  # noqa: E402
from .state_convert import convert_old_state  # noqa: E402

logger = logging.getLogger(__name__)

# The 2019 data uses the study's layout names; the current package renamed two.
_LAYOUT_ALIASES = {
    "random0": "forced_coordination",
    "random3": "counter_circuit_o_1order",
}


def _surface_to_bgr(surface: pygame.Surface) -> np.ndarray:
    arr = pygame.surfarray.array3d(surface)  # (W, H, 3), RGB
    return cv2.cvtColor(np.transpose(arr, (1, 0, 2)), cv2.COLOR_RGB2BGR)


def render_trial(trial: Trial, out_path: Path, cfg: RenderConfig | None = None) -> Path:
    cfg = cfg or RenderConfig()
    # old_dynamics=True is required: this data predates the ingredient-list soup rework
    layout = _LAYOUT_ALIASES.get(trial.layout_name, trial.layout_name)
    mdp = OvercookedGridworld.from_layout_name(layout, old_dynamics=True)
    visualizer = StateVisualizer()

    indices = list(range(0, len(trial), cfg.subsample))[: cfg.max_frames]
    writer = None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for i in indices:
        state = convert_old_state(trial.states[i])
        surface = visualizer.render_state(
            state=state,
            grid=mdp.terrain_mtx,
            hud_data={"score": int(trial.scores[i]), "time": int(trial.time_elapsed[i])},
        )
        frame = _surface_to_bgr(surface)
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), cfg.fps, (w, h))
        writer.write(frame)

    if writer is not None:
        writer.release()
    logger.info("rendered %s (%d frames) -> %s", trial.trial_id, len(indices), out_path)
    return out_path
