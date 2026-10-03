# What is where

| folder | made by | what |
|---|---|---|
| `pilot_2026-09/` | `main` before the readable render (tag `pilot-v1` has the code that scores it) | pilot 1: Qwen2.5-VL-7B 4-bit, 15 episodes, `telemetry` / `video_dense` / `video_sparse`, 8 claims per minute, hard-to-read clock and labels |
| `pilot_2026-09b/` | tag `pilot-v1` | pilot 2: the same, with the readable render. The README's pilot tables come from its `metrics.md` |
| `v2/rescored/pilot_2026-09*/` | `python analyze.py --run results/pilot_2026-09b --no-legacy --out results/v2/rescored/pilot_2026-09b` | both pilots' existing claims, re-scored with the study-v2 checker. No model was rerun |
| `v2/<model>/` | `run_study.sh`, phases `pilot` and `all` | study v2, one folder per model setting: `results.json` (every claim, raw output, review), `config.json` (model, revision, precision, prompt hash, git SHA), `report.md` (the reviews), `metrics.md` (the pilot's checker), `metrics_v2.md` (the v2 checker, all episodes), `metrics_v2_pilot15.md` (the pilot's 15 only), `figures/` |
| `v2/probe/<model>/` | `run_study.sh`, phase `probe` | one `.jsonl` per probe variant, one line per item |
| `v2/probe/probe_summary.md` | `scripts/analyze_probe.py` | probe accuracy by question, form and model; `probe_ladder.png` |
| `v2/variance/<model>_seed<k>/` | `run_study.sh`, phase `variance` | sampled decoding on the pilot's 15 episodes, log and 2 fps video |
| `v2/SUMMARY.md` | `scripts/analyze_study.py` | every model and condition side by side, model differences on the same episodes, the variance repeat |

Not committed: rendered videos (`*/videos/`, `v2/videos/`), probe frames and clips
(`v2/probe/media/`), smoke tests (`v2/smoke/`) and the logs (`logs/`). All of them
can be regenerated.

## How long study v2 takes

Measured in the smoke test (one minute of one episode, every condition) on the RTX
A5000s, shared with other jobs:

| model setting | one minute, all 7 conditions | one episode (3 min) | 76 episodes |
|---|---|---|---|
| `qwen25vl7b_4bit` | 8 min | ~25 min | ~32 h |
| `qwen25vl7b_bf16` (split over both cards) | 7 min | ~21 min | ~27 h |
| `qwen3vl8b_bf16` (split over both cards) | 20 min* | ~45-60 min | ~55-75 h |

\* Qwen3-VL ignores the 20-claim cap and writes until the token limit; that minute
included a retry. The token limit is now lower and cut-off output is recovered, so
expect it to be faster than this.

The probe is ~1-3 h per model setting, the variance repeat ~4-8 h. **The whole study is
about 5-6 days of GPU time.** The pilot's 15 episodes for all three settings
(directly comparable with the pilot) come first, after roughly the first day. To get
results sooner, run fewer episodes (`EPISODES=30`) or skip steps (`PHASES=...`).

Claims past the cap are dropped and counted (`claims_over_cap` per minute in
`results.json`), and output cut off at the token limit is marked `truncated`.
