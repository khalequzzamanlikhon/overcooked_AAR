"""Run the comparison: one episode at a time, three conditions each.

    python run_pipeline.py --layout all --n-trials 3 --out results/pilot
    python run_pipeline.py --no-llm            # render + timelines only

Conditions (same model, same prompts, same minute boundaries):
    telemetry      the event log as text
    video_dense    the video at 2 frames per second of play
    video_sparse   the video at 1 frame per 3 seconds of play

Everything lands in <out>/results.json, checkpointed after every episode.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from aar.config import (
    CONDITIONS,
    LAYOUTS,
    SEGMENT_SECONDS,
    VIDEO_FPS_DENSE,
    VIDEO_FPS_SPARSE,
    DataConfig,
    LLMConfig,
    RenderConfig,
)
from aar.data_loader import load_trials
from aar.generate_aar import aar_from_claims, claims_from_timeline, claims_from_video, init_backend
from aar.render_video import render_trial
from aar.telemetry_to_text import events_to_timeline, extract_events, segment_events
from aar.verify import true_deliveries, verify_segment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_FPS = {"video_dense": VIDEO_FPS_DENSE, "video_sparse": VIDEO_FPS_SPARSE}


def pick_trials(layout: str, n: int, pickle_name: str):
    trials = load_trials(pickle_name, layout=layout)
    trials.sort(key=lambda t: t.final_score)  # spread the picks across the score range
    if n < len(trials):
        step = len(trials) / n
        trials = [trials[int(i * step)] for i in range(n)]
    return trials


def write_report(records: list[dict], path: Path) -> None:
    lines = ["# After-action reviews", ""]
    for rec in records:
        lines += [
            f"## {rec['trial_id']}",
            f"Layout: {rec['layout']} | final score {int(rec['final_score'])} | "
            f"{rec['n_events']} logged events | {rec['true_deliveries']} deliveries",
            "",
        ]
        for condition in CONDITIONS:
            block = rec["conditions"].get(condition)
            if block:
                lines += [f"### {condition}", "", block["aar"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(args: argparse.Namespace) -> None:
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    data_cfg, render_cfg = DataConfig(), RenderConfig()
    llm_cfg = LLMConfig(model_id=args.model, device=args.device, load_in_4bit=not args.bf16)
    use_llm = not args.no_llm
    conditions = [c for c in CONDITIONS if c in args.conditions]

    if use_llm:
        t0 = time.time()
        init_backend(llm_cfg)
        logger.info("backend ready in %.1fs", time.time() - t0)

    (out_dir / "config.json").write_text(
        json.dumps(
            {
                "model": llm_cfg.model_id,
                "load_in_4bit": llm_cfg.load_in_4bit,
                "conditions": conditions,
                "video_fps": _FPS,
                "segment_seconds": SEGMENT_SECONDS,
                "render": {"real_time": True, "player_labels": render_cfg.label_players},
                "split": args.split,
            },
            indent=2,
        )
    )

    pickle_name = data_cfg.train_pickle_name if args.split == "train" else data_cfg.test_pickle_name
    layouts = list(LAYOUTS) if args.layout == "all" else [args.layout]
    records: list[dict] = []

    for layout in layouts:
        for trial in pick_trials(layout, args.n_trials, pickle_name):
            t0 = time.time()
            events = extract_events(trial)
            logger.info("%s score=%d steps=%d events=%d", trial.trial_id, trial.final_score, len(trial), len(events))

            full_video, segments = render_trial(trial, out_dir / "videos", render_cfg)
            (out_dir / "timelines").mkdir(parents=True, exist_ok=True)
            timelines = {}
            for start, end, _ in segments:
                timelines[start] = events_to_timeline(trial, events, start, end)
            (out_dir / "timelines" / f"{trial.trial_id}.txt").write_text(
                "\n\n".join(timelines[s] for s, _, _ in segments)
            )

            record = {
                "trial_id": trial.trial_id,
                "layout": trial.layout_name,
                "final_score": trial.final_score,
                "duration_s": round(trial.time_elapsed[-1], 1),
                "n_events": len(events),
                "true_deliveries": true_deliveries(events),
                "video": str(full_video),
                "events": [e.as_dict() for e in events],
                "segments": [
                    {
                        "start": s,
                        "end": e,
                        "video": str(p),
                        "true_deliveries": true_deliveries(segment_events(events, s, e)),
                    }
                    for s, e, p in segments
                ],
                "conditions": {},
            }

            if use_llm:
                for condition in conditions:
                    seg_results, all_claims = [], []
                    for start, end, seg_video in segments:
                        t1 = time.time()
                        if condition == "telemetry":
                            got = claims_from_timeline(timelines[start], start, end, llm_cfg)
                        else:
                            got = claims_from_video(seg_video, start, end, _FPS[condition], llm_cfg)
                        seg_events = segment_events(events, start, end)
                        checked = verify_segment(got["claims"], seg_events)
                        seg_results.append(
                            {
                                "start": start,
                                "end": end,
                                "deliveries_claimed": got["deliveries"],
                                "deliveries_true": true_deliveries(seg_events),
                                "parse_failed": got.get("parse_failed", False),
                                "claims": checked,
                                "seconds": round(time.time() - t1, 1),
                            }
                        )
                        all_claims += got["claims"]
                    aar = aar_from_claims(all_claims, trial.layout_name, trial.final_score, llm_cfg)
                    record["conditions"][condition] = {"segments": seg_results, "aar": aar}
                    logger.info("  %s: %d claims", condition, len(all_claims))

            record["seconds"] = round(time.time() - t0, 1)
            records.append(record)
            (out_dir / "results.json").write_text(json.dumps(records, indent=2))
            logger.info("  episode done in %.1fs", record["seconds"])

    write_report(records, out_dir / "report.md")
    logger.info("wrote %d episodes -> %s", len(records), out_dir / "results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", default="all", help=f"one of {LAYOUTS}, or 'all'")
    parser.add_argument("--n-trials", type=int, default=3, help="episodes per layout")
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--out", type=Path, default=Path("results/run"))
    parser.add_argument("--model", default=LLMConfig.model_id)
    parser.add_argument("--device", default=LLMConfig.device)
    parser.add_argument("--bf16", action="store_true", help="load in bf16 instead of 4-bit (needs ~17 GB)")
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--no-llm", action="store_true")
    main(parser.parse_args())
