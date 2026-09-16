"""Build the README demo assets from a pipeline run.

    python run_pipeline.py --layout all --n-trials 1 --out out_all --no-llm
    python scripts/make_demo_assets.py --run out_all --out docs/demo
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def _read_frames(video: Path, every: int, limit: int, width: int) -> list[Image.Image]:
    cap = cv2.VideoCapture(str(video))
    frames, i = [], 0
    while len(frames) < limit:
        ok, frame = cap.read()
        if not ok:
            break
        if i % every == 0:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
            frames.append(img)
        i += 1
    cap.release()
    return frames


def make_gif(video: Path, out: Path, width: int = 320, every: int = 3, limit: int = 110) -> None:
    frames = _read_frames(video, every, limit, width)
    frames = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)


def make_layout_grid(records: list[dict], out: Path, tile_w: int = 300) -> None:
    tiles = []
    for rec in records:
        frames = _read_frames(Path(rec["video"]), 1, 120, tile_w)
        img = frames[-1].copy()
        label = f"{rec['layout']}  (score {int(rec['final_score'])})"
        canvas = Image.new("RGB", (tile_w, img.height + 26), "white")
        canvas.paste(img, (0, 26))
        ImageDraw.Draw(canvas).text((6, 6), label, fill="black")
        tiles.append(canvas)
    h = max(t.height for t in tiles)
    grid = Image.new("RGB", (tile_w * len(tiles) + 8 * (len(tiles) - 1), h), "white")
    for i, t in enumerate(tiles):
        grid.paste(t, (i * (tile_w + 8), 0))
    grid.save(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("out_all"))
    parser.add_argument("--out", type=Path, default=Path("docs/demo"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    records = json.loads((args.run / "results.json").read_text())
    make_layout_grid(records, args.out / "layouts.png")
    for rec in records:
        make_gif(Path(rec["video"]), args.out / f"{rec['layout']}.gif")
        timeline = (args.run / "timelines" / f"{rec['trial_id']}.txt").read_text()
        (args.out / f"{rec['layout']}_timeline.txt").write_text(timeline)
    print(f"wrote demo assets -> {args.out}")
