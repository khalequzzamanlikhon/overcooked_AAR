"""Ask one model every probe item, in every variant (video / text / fps / HUD).

    python scripts/probe_run.py --model Qwen/Qwen2.5-VL-7B-Instruct --out results/v2/probe/qwen25vl7b_4bit
    python scripts/probe_run.py --model Qwen/Qwen3-VL-8B-Instruct --bf16 --device auto --out ...

Writes <out>/<variant>.jsonl, one line per item, and skips items already
answered, so it can be stopped and restarted.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aar import vlm_local  # noqa: E402
from aar.config import LLMConfig, RenderConfig  # noqa: E402
from aar.probe import VARIANTS, ensure_media, parse_answer, prompt_for, score, variant_types  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("probe")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=Path("probes/probe_v1.jsonl"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--media", type=Path, default=Path("results/v2/probe/media"))
    parser.add_argument("--model", default=LLMConfig.model_id)
    parser.add_argument("--device", default=LLMConfig.device)
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS))
    parser.add_argument("--limit", type=int, default=0, help="only the first N items per variant (smoke tests)")
    args = parser.parse_args()

    items = [json.loads(line) for line in args.items.read_text(encoding="utf-8").splitlines() if line.strip()]
    vlm_local.load_backend(args.model, args.device, not args.bf16)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "config.json").write_text(json.dumps(
        {"model": args.model, "precision": "bf16" if args.bf16 else "nf4-4bit", "items": str(args.items),
         "n_items": len(items), "model_revision": vlm_local.model_revision()}, indent=2))

    # trials only for rendering; loaded lazily because it takes a while
    trials = None
    renderers: dict = {}

    def renderer_for(trial_id: str, hud: str):
        nonlocal trials
        from aar.render_video import FrameRenderer
        from run_pipeline import select_episodes

        if trials is None:
            trials = {t.trial_id: t for t, _, _ in select_episodes("all")}
        key = (trial_id, hud)
        if key not in renderers:
            renderers.clear()  # one trial at a time is plenty; items are grouped by trial below
            renderers[key] = FrameRenderer(trials[trial_id], replace(RenderConfig(), hud=hud))
        return renderers[key]

    for variant in args.variants:
        form, hud, fps = VARIANTS[variant]
        wanted = variant_types(variant)
        todo = [it for it in items if it["qtype"] in wanted]
        if args.limit:  # a few of every question type, so a smoke test touches frames and clips
            per_type = max(1, -(-args.limit // len(wanted)))
            kept: dict[str, list] = {}
            for it in todo:
                bucket = kept.setdefault(it["qtype"], [])
                if len(bucket) < per_type:
                    bucket.append(it)
            todo = [it for bucket in kept.values() for it in bucket]
        path = args.out / f"{variant}.jsonl"
        done = set()
        if path.exists():
            done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
        todo = sorted((it for it in todo if it["id"] not in done), key=lambda it: (it["trial_id"], it["id"]))
        logger.info("%s: %d items to go (%d done)", variant, len(todo), len(done))
        t_start, correct = time.time(), 0
        with path.open("a", encoding="utf-8") as f:
            for n, item in enumerate(todo, 1):
                prompt = prompt_for(item, form, hud)
                t0 = time.time()
                try:
                    if form == "text":
                        raw = vlm_local.generate_text(prompt, max_new_tokens=24)
                    else:
                        media = ensure_media(item, renderer_for(item["trial_id"], hud), hud, args.media)
                        if item["input"]["kind"] == "frame":
                            raw = vlm_local.generate_from_image(media, prompt, max_new_tokens=24)
                        else:
                            raw = vlm_local.generate_from_video(media, prompt, fps, max_new_tokens=24)
                    error = None
                except Exception as exc:  # noqa: BLE001
                    logger.exception("item %s failed", item["id"])
                    raw, error = "", repr(exc)
                answer = parse_answer(item, raw)
                result = score(item, answer)
                correct += result["correct"]
                f.write(json.dumps({"id": item["id"], "qtype": item["qtype"], "level": item["level"],
                                    "trial_id": item["trial_id"], "layout": item["layout"], "gold": item["gold"],
                                    "raw": raw[:200], "answer": answer, **result, "error": error,
                                    "seconds": round(time.time() - t0, 2)}) + "\n")
                f.flush()
                if n % 100 == 0 or n == len(todo):
                    logger.info("  %s %d/%d  running accuracy %.2f  (%.1f items/min)", variant, n, len(todo),
                                correct / n, n / max(time.time() - t_start, 1e-6) * 60)


if __name__ == "__main__":
    main()
