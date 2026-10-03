#!/usr/bin/env bash
# One model, one set of episodes, in the foreground. For the whole study
# (both models, the probe, all 76 episodes, in the background) use run_study.sh.
#
#   bash run.sh                      # the pilot's 15 episodes, every condition, Qwen2.5-VL-7B 4-bit
#   EPISODES=3 bash run.sh           # the first 3 episodes
#   GPU=1 MODEL=Qwen/Qwen3-VL-8B-Instruct BF16=1 bash run.sh
#
# Needs a CUDA GPU with ~10 GB free for the 7B in 4-bit (~17 GB in bf16).
# Without one, use NO_LLM=1 to render the videos and event logs only.

set -euo pipefail

EPISODES="${EPISODES:-pilot}"
MODEL="${MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
OUT="${OUT:-results/run_$(date +%Y-%m-%d)}"
GPU="${GPU:-0}"
BF16_FLAG=$([[ "${BF16:-0}" == "1" ]] && echo "--bf16" || true)

export SDL_VIDEODRIVER=dummy          # pygame needs a driver even headless
export TOKENIZERS_PARALLELISM=false
export CUDA_VISIBLE_DEVICES="$GPU"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [[ "${NO_LLM:-0}" == "1" ]]; then
  python run_pipeline.py --episodes "$EPISODES" --out "$OUT" --no-llm
  exit 0
fi

python run_pipeline.py --episodes "$EPISODES" --out "$OUT" --model "$MODEL" $BF16_FLAG
python analyze.py --run "$OUT"

echo
echo "  $OUT/report.md        the reviews, readable"
echo "  $OUT/metrics_v2.md    claim checks against the log, with confidence intervals"
echo "  $OUT/videos/          gameplay videos, real time"
echo
echo "Next, rate them blind:  python rate_aars.py --run $OUT --rater <your name>"
