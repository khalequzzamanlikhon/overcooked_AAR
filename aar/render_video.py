"""Render a trial into mp4s -- this is how the video condition gets a modality
without recording anyone playing.

Two choices matter for the comparison:

* Real time. The data runs at ~6.7 states per second and the video is written
  at that rate, so one second of video is one second of gameplay. The first
  version rendered every 4th state at 10 fps, which is 6x speed: sampled at
  2 fps the model then saw one frame per 3 s of play and could not see a
  blocked move at all.
* Player labels. The chefs wear a blue and a green hat; the log calls them
  Player 1 and Player 2. Without a label on screen, a claim about "the blue
  chef" cannot be matched to a claim about "Player 1", so P1/P2 is drawn over
  each chef the way a game shows name tags.

Headless note: pygame needs a video driver. SDL_VIDEODRIVER=dummy is set here
so rendering works on a server with no display.
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
from .telemetry_to_text import LAYOUT_ALIASES  # noqa: E402

logger = logging.getLogger(__name__)

_LABEL_COLORS = [(255, 200, 80), (120, 255, 160)]  # BGR, close to the hat colours


def _surface_to_bgr(surface: pygame.Surface) -> np.ndarray:
    arr = pygame.surfarray.array3d(surface)  # (W, H, 3), RGB
    return cv2.cvtColor(np.transpose(arr, (1, 0, 2)), cv2.COLOR_RGB2BGR)


def _label_players(frame: np.ndarray, state: dict, tile: int, rows: int) -> None:
    """Draw P1/P2 over the chefs. The HUD sits above the grid, so the grid
    starts at (frame height - rows * tile)."""
    grid_top = frame.shape[0] - rows * tile
    for i, player in enumerate(state["players"]):
        x, y = player["position"]
        org = (int(x * tile) + 4, grid_top + int(y * tile) + 16)
        cv2.putText(frame, f"P{i + 1}", org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, f"P{i + 1}", org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, _LABEL_COLORS[i], 1, cv2.LINE_AA)


def render_trial(
    trial: Trial, out_dir: Path, cfg: RenderConfig | None = None
) -> tuple[Path, list[tuple[float, float, Path]]]:
    """Write the full episode and one mp4 per segment.

    Returns (full_video, [(start_s, end_s, segment_path), ...]).
    """
    cfg = cfg or RenderConfig()
    layout = LAYOUT_ALIASES.get(trial.layout_name, trial.layout_name)
    mdp = OvercookedGridworld.from_layout_name(layout, old_dynamics=True)
    rows = len(mdp.terrain_mtx)
    visualizer = StateVisualizer(tile_size=cfg.tile_size)

    duration = trial.time_elapsed[-1]
    fps = (len(trial) - 1) / duration / cfg.subsample  # ~6.7, i.e. real time
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / f"{trial.trial_id}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    full_writer = None
    seg_writers: dict[int, cv2.VideoWriter] = {}
    segments: dict[int, tuple[float, float, Path]] = {}

    for i in range(0, len(trial), cfg.subsample):
        state = convert_old_state(trial.states[i])
        surface = visualizer.render_state(
            state=state,
            grid=mdp.terrain_mtx,
            hud_data={"score": int(trial.scores[i]), "time": int(trial.time_elapsed[i])},
        )
        frame = _surface_to_bgr(surface)
        if cfg.label_players:
            _label_players(frame, trial.states[i], cfg.tile_size, rows)

        h, w = frame.shape[:2]
        if full_writer is None:
            full_writer = cv2.VideoWriter(str(full_path), fourcc, fps, (w, h))
        full_writer.write(frame)

        seg = int(trial.time_elapsed[i] // cfg.segment_seconds)
        if seg * cfg.segment_seconds > duration - 10:
            seg -= 1  # a few leftover seconds belong to the last minute
        if seg not in seg_writers:
            path = out_dir / f"{trial.trial_id}_seg{seg}.mp4"
            seg_writers[seg] = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
            segments[seg] = (seg * cfg.segment_seconds, (seg + 1) * cfg.segment_seconds, path)
        seg_writers[seg].write(frame)

    if full_writer is not None:
        full_writer.release()
    for writer in seg_writers.values():
        writer.release()

    logger.info("rendered %s (%.0f s, %.1f fps) -> %s", trial.trial_id, duration, fps, full_path)
    return full_path, [segments[k] for k in sorted(segments)]
