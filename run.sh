#!/usr/bin/env bash
# Run the whole comparison with one command.
#
#   bash run.sh                      # 3 episodes per layout, all three conditions
#   N_TRIALS=1 LAYOUT=cramped_room bash run.sh
#   GPU=1 MODEL=Qwen/Qwen2.5-VL-3B-Instruct bash run.sh
#
# Needs a CUDA GPU with ~10 GB free for the 7B in 4-bit. Without one, use
# NO_LLM=1 to render the videos and event logs only.

set -euo pipefail

LAYOUT="${LAYOUT:-all}"
N_TRIALS="${N_TRIALS:-3}"
MODEL="${MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
OUT="${OUT:-results/run_$(date +%Y-%m-%d)}"
GPU="${GPU:-0}"

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
  python run_pipeline.py --layout "$LAYOUT" --n-trials "$N_TRIALS" --out "$OUT" --no-llm
  exit 0
fi

python run_pipeline.py --layout "$LAYOUT" --n-trials "$N_TRIALS" --out "$OUT" --model "$MODEL"
python analyze.py --run "$OUT"

echo
echo "  $OUT/report.md     the reviews, readable"
echo "  $OUT/metrics.md    claim checks against the log"
echo "  $OUT/videos/       gameplay videos, real time"
echo
echo "Next, rate them blind:  python rate_aars.py --run $OUT --rater <your name>"
