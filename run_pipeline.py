"""Run the comparison: one episode at a time, every condition for each.

    python run_pipeline.py --episodes pilot --out results/v2/qwen25vl7b_4bit
    python run_pipeline.py --episodes all --model Qwen/Qwen3-VL-8B-Instruct --bf16 --device auto --out ...
    python run_pipeline.py --episodes 1 --no-llm            # render + timelines only

Episodes:
    pilot   the pilot's 15 (3 per layout from the train split, spread across the score range)
    all     all 76 episodes (39 train + 37 test), the pilot's 15 first
    N       the first N of `all`

Conditions (same model, same prompts, same minute boundaries; see aar/config.py):
    blind, telemetry, video_dense, video_sparse, video_log, state_text, oracle

Everything lands in <out>/results.json, saved after every condition, and a
rerun with the same --out picks up where the last one stopped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import subprocess
import time
from pathlib import Path

from aar import prompts
from aar.behaviors import detect_behaviors
from aar.config import (
    CLAIM_CAP,
    CONDITIONS,
    LAYOUTS,
    SEGMENT_SECONDS,
    VIDEO_FPS_DENSE,
    VIDEO_FPS_SPARSE,
    DataConfig,
    LLMConfig,
    RenderConfig,
)
from aar.data_loader import Trial, load_trials
from aar.generate_aar import aar_from_claims, claims_for_condition, init_backend, oracle_claims
from aar.render_video import render_trial
from aar.state_text import segment_state_text
from aar.telemetry_to_text import events_to_timeline, extract_events, segment_bounds, segment_events, terrain_for
from aar.verify import true_deliveries, verify_segment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_FPS = {"video_dense": VIDEO_FPS_DENSE, "video_sparse": VIDEO_FPS_SPARSE, "video_log": VIDEO_FPS_DENSE}
BEHAVIOR_SCALES = ("0.5", "1.0", "1.5")


def pick_trials(layout: str, n: int, pickle_name: str) -> list[Trial]:
    trials = load_trials(pickle_name, layout=layout)
    trials.sort(key=lambda t: t.final_score)  # spread the picks across the score range
    if n < len(trials):
        step = len(trials) / n
        trials = [trials[int(i * step)] for i in range(n)]
    return trials


def select_episodes(spec: str, layout: str = "all") -> list[tuple[Trial, str, bool]]:
    """[(trial, split, in_pilot)], the pilot's 15 first so early results are comparable."""
    data = DataConfig()
    layouts = list(LAYOUTS) if layout == "all" else [layout]
    pilot = [t for lay in layouts for t in pick_trials(lay, 3, data.train_pickle_name)]
    pilot_ids = {t.trial_id for t in pilot}
    out = [(t, "train", True) for t in pilot]
    if spec == "pilot":
        return out
    train_ids = set()
    for lay in layouts:
        for t in load_trials(data.train_pickle_name, layout=lay):
            train_ids.add(t.trial_id)
            if t.trial_id not in pilot_ids:
                out.append((t, "train", False))
    for lay in layouts:
        for t in load_trials(data.test_pickle_name, layout=lay):
            if t.trial_id in train_ids:  # never seen so far, but ids are only unique within a split
                t.trial_id = f"test_{t.trial_id}"
            out.append((t, "test", False))
    return out if spec == "all" else out[: int(spec)]


def ensure_videos(trial: Trial, cache: Path, cfg: RenderConfig) -> tuple[Path, list[tuple[float, float, Path]]]:
    """Render once, reuse across models and reruns."""
    bounds = segment_bounds(trial.time_elapsed[-1], cfg.segment_seconds)
    full = cache / f"{trial.trial_id}.mp4"
    segs = [(s, e, cache / f"{trial.trial_id}_seg{k}.mp4") for k, (s, e) in enumerate(bounds)]
    if full.exists() and all(p.exists() and p.stat().st_size > 0 for _, _, p in segs):
        return full, segs
    return render_trial(trial, cache, cfg)


def write_report(records: list[dict], path: Path, conditions: list[str]) -> None:
    lines = ["# After-action reviews", ""]
    for rec in records:
        lines += [
            f"## {rec['trial_id']}",
            f"Layout: {rec['layout']} | final score {int(rec['final_score'])} | "
            f"{rec['n_events']} logged events | {rec['true_deliveries']} deliveries",
            "",
        ]
        for condition in conditions:
            block = rec["conditions"].get(condition)
            if block:
                lines += [f"### {condition}", "", block["aar"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def run_condition(condition, trial, events, all_events, segments, timelines, states, llm_cfg, cap) -> dict:
    if condition == "oracle":
        claims = oracle_claims(all_events)
        return {"segments": [], "n_claims": len(claims), "aar": aar_from_claims(claims, trial.layout_name,
                                                                                 trial.final_score, llm_cfg)}
    seg_results, all_claims, incomplete = [], [], False
    for start, end, seg_video in segments:
        t1 = time.time()
        seg_events = segment_events(events, start, end)
        try:
            got = claims_for_condition(
                condition, start, end, llm_cfg, log=timelines[start], state=states.get(start, ""),
                layout=trial.layout_name, video=seg_video, fps=_FPS.get(condition, VIDEO_FPS_DENSE), cap=cap,
            )
            error = None
        except Exception as exc:  # noqa: BLE001  (an OOM on one minute should not end the run)
            logger.exception("    %s %.0f-%.0fs failed", condition, start, end)
            got, error, incomplete = {"deliveries": None, "claims": [], "parse_failed": True}, repr(exc), True
            try:
                import torch

                torch.cuda.empty_cache()
            except Exception:  # noqa: BLE001
                pass
        seg_results.append(
            {
                "start": start,
                "end": end,
                "deliveries_claimed": got["deliveries"],
                "deliveries_true": true_deliveries(seg_events),
                "parse_failed": got.get("parse_failed", False),
                "retried": got.get("retried", False),
                "truncated": got.get("truncated", False),
                "claims_over_cap": got.get("claims_over_cap", 0),
                "claims": verify_segment(got["claims"], seg_events),  # legacy verdicts
                "raw": got.get("raw", "")[:4000],
                "error": error,
                "seconds": round(time.time() - t1, 1),
            }
        )
        all_claims += got["claims"]
        logger.info("    %s %3.0f-%3.0fs: %2d claims in %5.1fs%s", condition, start, end, len(got["claims"]),
                    time.time() - t1, " (ERROR)" if error else "")
    aar = aar_from_claims(all_claims, trial.layout_name, trial.final_score, llm_cfg)
    return {"segments": seg_results, "aar": aar, "incomplete": incomplete}


def main(args: argparse.Namespace) -> None:
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    render_cfg = RenderConfig()
    llm_cfg = LLMConfig(model_id=args.model, device=args.device, load_in_4bit=not args.bf16,
                        do_sample=args.do_sample, seed=args.seed)
    use_llm = not args.no_llm
    conditions = [c for c in CONDITIONS if c in args.conditions]
    video_cache: Path = args.video_cache or out_dir / "videos"

    results_path = out_dir / "results.json"
    records: list[dict] = json.loads(results_path.read_text()) if results_path.exists() else []
    by_id = {r["trial_id"]: r for r in records}

    if use_llm:
        t0 = time.time()
        init_backend(llm_cfg)
        logger.info("backend ready in %.1fs", time.time() - t0)

    from aar import vlm_local
    import transformers

    (out_dir / "config.json").write_text(
        json.dumps(
            {
                "model": llm_cfg.model_id,
                "model_revision": vlm_local.model_revision() if use_llm else None,
                "precision": "nf4-4bit" if llm_cfg.load_in_4bit else "bf16",
                "decoding": {"do_sample": llm_cfg.do_sample, "seed": llm_cfg.seed,
                             "max_new_tokens": llm_cfg.max_new_tokens},
                "transformers": transformers.__version__,
                "prompt_version": prompts.prompt_version(),
                "git_sha": _git_sha(),
                "claim_cap": args.claim_cap,
                "conditions": conditions,
                "episodes": args.episodes,
                "video_fps": _FPS,
                "segment_seconds": SEGMENT_SECONDS,
                "render": {"real_time": True, "player_labels": render_cfg.label_players, "hud": render_cfg.hud},
                "behavior_scales": BEHAVIOR_SCALES,
                "started": dt.datetime.now().isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )

    episodes = select_episodes(args.episodes, args.layout)
    logger.info("%d episodes, conditions %s", len(episodes), conditions)
    for n, (trial, split, in_pilot) in enumerate(episodes, 1):
        rec = by_id.get(trial.trial_id)
        todo = [c for c in conditions if use_llm and (rec is None or c not in rec["conditions"]
                                                      or rec["conditions"][c].get("incomplete"))]
        if rec is not None and not todo:
            continue
        t0 = time.time()
        events = extract_events(trial)
        terrain = terrain_for(trial)
        behaviors = {s: [e.as_dict() for e in detect_behaviors(trial, terrain, float(s))] for s in BEHAVIOR_SCALES}
        full_video, segments = ensure_videos(trial, video_cache, render_cfg)
        if args.max_segments:
            segments = segments[: args.max_segments]
        logger.info("[%d/%d] %s (%s) score=%d events=%d behaviours=%d", n, len(episodes), trial.trial_id, split,
                    trial.final_score, len(events), len(behaviors["1.0"]))

        timelines = {s: events_to_timeline(trial, events, s, e) for s, e, _ in segments}
        states = {s: segment_state_text(trial, terrain, s, e) for s, e, _ in segments} if "state_text" in todo else {}
        (out_dir / "timelines").mkdir(parents=True, exist_ok=True)
        (out_dir / "timelines" / f"{trial.trial_id}.txt").write_text("\n\n".join(timelines[s] for s, _, _ in segments))

        if rec is None:
            rec = {
                "trial_id": trial.trial_id,
                "split": split,
                "pilot_subset": in_pilot,
                "layout": trial.layout_name,
                "final_score": trial.final_score,
                "duration_s": round(trial.time_elapsed[-1], 1),
                "n_events": len(events),
                "true_deliveries": true_deliveries(events),
                "video": str(full_video),
                "events": [e.as_dict() for e in events],
                "behaviors": behaviors,
                "segments": [
                    {"start": s, "end": e, "video": str(p), "true_deliveries": true_deliveries(segment_events(events, s, e))}
                    for s, e, p in segments
                ],
                "conditions": {},
            }
            records.append(rec)
            by_id[trial.trial_id] = rec

        all_events = sorted(rec["events"] + rec["behaviors"]["1.0"], key=lambda e: e["seconds"])
        for condition in todo:
            t1 = time.time()
            rec["conditions"][condition] = run_condition(condition, trial, events, all_events, segments, timelines,
                                                         states, llm_cfg, args.claim_cap)
            logger.info("  %s done in %.0fs", condition, time.time() - t1)
            results_path.write_text(json.dumps(records, indent=2))
        rec["seconds"] = round(rec.get("seconds", 0) + time.time() - t0, 1)
        results_path.write_text(json.dumps(records, indent=2))
        logger.info("  episode done in %.0fs", time.time() - t0)

    write_report(records, out_dir / "report.md", conditions)
    logger.info("wrote %d episodes -> %s", len(records), results_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", default="pilot", help="pilot | all | N")
    parser.add_argument("--layout", default="all", help=f"one of {LAYOUTS}, or 'all'")
    parser.add_argument("--out", type=Path, default=Path("results/run"))
    parser.add_argument("--video-cache", type=Path, default=None, help="where rendered videos live (default <out>/videos)")
    parser.add_argument("--model", default=LLMConfig.model_id)
    parser.add_argument("--device", default=LLMConfig.device, help='"cuda:0", or "auto" to spread over all visible GPUs')
    parser.add_argument("--bf16", action="store_true", help="load in bf16 instead of 4-bit (needs ~17 GB)")
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--claim-cap", type=int, default=CLAIM_CAP)
    parser.add_argument("--do-sample", action="store_true", help="sampled decoding (variance repeat); default greedy")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-segments", type=int, default=0, help="only the first N minutes (smoke tests)")
    parser.add_argument("--no-llm", action="store_true")
    main(parser.parse_args())
