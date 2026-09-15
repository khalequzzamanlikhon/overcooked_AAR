"""End-to-end: load trials -> render video -> build timeline -> generate + compare AARs.

    python run_pipeline.py --layout cramped_room --n-trials 6 --out out/
    python run_pipeline.py --device cuda:1 --model Qwen/Qwen2.5-VL-3B-Instruct
    python run_pipeline.py --no-llm          # render + timelines only, no model load
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from aar.config import LAYOUTS, DataConfig, LLMConfig, RenderConfig
from aar.data_loader import load_trials
from aar.generate_aar import aar_from_telemetry, aar_from_video, compare_aars, init_backend
from aar.render_video import render_trial
from aar.telemetry_to_text import events_to_timeline, extract_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def write_report(records: list[dict], out_path: Path) -> None:
    """Human-readable markdown of every AAR pair, for skimming after the run."""
    lines = ["# Overcooked AAR results", ""]
    for rec in records:
        lines += [
            f"## {rec['trial_id']}",
            f"Layout: {rec['layout']} | Final score: {int(rec['final_score'])} | Events: {rec['n_events']}",
            "",
        ]
        for key, heading in [
            ("aar_telemetry", "AAR from telemetry"),
            ("aar_video", "AAR from video"),
            ("comparison", "Where they differ"),
        ]:
            if rec.get(key):
                lines += [f"### {heading}", "", rec[key], ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(args: argparse.Namespace) -> None:
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    data_cfg, render_cfg = DataConfig(), RenderConfig()
    llm_cfg = LLMConfig(backend=args.backend, local_model_id=args.model, device=args.device)

    layouts = list(LAYOUTS) if args.layout == "all" else [args.layout]
    use_llm = not args.no_llm

    if use_llm:
        t0 = time.time()
        init_backend(llm_cfg)
        logger.info("backend ready in %.1fs", time.time() - t0)

    records: list[dict] = []
    for layout in layouts:
        trials = load_trials(data_cfg.train_pickle_name, layout=layout)
        trials.sort(key=lambda t: t.final_score)  # spread picks across the score range
        if args.n_trials < len(trials):
            step = len(trials) / args.n_trials
            trials = [trials[int(i * step)] for i in range(args.n_trials)]

        for trial in trials:
            t0 = time.time()
            logger.info("%s (score=%d, %d steps)", trial.trial_id, trial.final_score, len(trial))
            video_path = render_trial(trial, out_dir / "videos" / f"{trial.trial_id}.mp4", render_cfg)

            events = extract_events(trial)
            timeline = events_to_timeline(trial, events)
            (out_dir / "timelines").mkdir(parents=True, exist_ok=True)
            (out_dir / "timelines" / f"{trial.trial_id}.txt").write_text(timeline)

            record = {
                "trial_id": trial.trial_id,
                "layout": trial.layout_name,
                "final_score": trial.final_score,
                "n_events": len(events),
                "video": str(video_path),
            }
            if use_llm:
                record["aar_telemetry"] = aar_from_telemetry(timeline, llm_cfg)
                record["aar_video"] = aar_from_video(video_path, llm_cfg)
                record["comparison"] = compare_aars(record["aar_telemetry"], record["aar_video"], llm_cfg)
            record["seconds"] = round(time.time() - t0, 1)

            records.append(record)
            (out_dir / "results.json").write_text(json.dumps(records, indent=2))  # checkpoint each trial
            logger.info("  done in %.1fs", record["seconds"])

    write_report(records, out_dir / "report.md")
    logger.info("wrote %d records -> %s", len(records), out_dir / "results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", default="cramped_room", help=f"one of {LAYOUTS}, or 'all'")
    parser.add_argument("--n-trials", type=int, default=6, help="per layout")
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--backend", choices=["local", "api"], default="local")
    parser.add_argument("--model", default=LLMConfig.local_model_id)
    parser.add_argument("--device", default="auto", help="'auto', 'cuda:0', 'cuda:1'")
    parser.add_argument("--no-llm", action="store_true")
    main(parser.parse_args())
