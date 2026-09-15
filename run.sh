#!/usr/bin/env bash
# Run the whole pipeline with one command.
#
#   bash run.sh
#
# Picks a backend automatically:
#   CUDA available          -> local Qwen2.5-VL on your GPU
#   No CUDA, API keys set   -> Groq (text) + Gemini (video)
#   Neither                 -> render + timelines only, and tells you why
#
# Overrides, all environment variables:
#   BACKEND=api|local|none   force a backend
#   GPU=1                    pin to cuda:1
#   LAYOUT=all               all five layouts (default: cramped_room)
#   N_TRIALS=4               trials per layout (default: 6)
#   MODEL=Qwen/Qwen2.5-VL-3B-Instruct   smaller local model
#   OUT=results              output directory (default: out)
#
# Everything lands in $OUT/ : videos/, timelines/, results.json, report.md

set -euo pipefail

LAYOUT="${LAYOUT:-cramped_room}"
N_TRIALS="${N_TRIALS:-6}"
MODEL="${MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
OUT="${OUT:-out}"
GPU="${GPU:-}"
BACKEND="${BACKEND:-}"

export SDL_VIDEODRIVER=dummy              # pygame needs a driver even headless
export HF_HOME="${HF_HOME:-$PWD/.hf_cache}"  # keep weights beside the project
export TOKENIZERS_PARALLELISM=false

echo "=== 1/4  setup ==="
if [[ ! -d .venv ]]; then
  echo "creating venv"
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --upgrade pip

# Core deps are small and CPU-only. Torch/transformers are a ~2GB install and
# are pointless without a GPU, so only pull them if one is actually present.
pip install -q -r requirements.txt

echo
echo "=== 2/4  detecting backend ==="
HAS_CUDA=$(python -c "
try:
    import torch; print('1' if torch.cuda.is_available() else '0')
except ImportError:
    print('0')
" 2>/dev/null || echo 0)

if [[ -z "$BACKEND" ]]; then
  if [[ "$HAS_CUDA" == "1" ]]; then
    BACKEND=local
  elif [[ -n "${GROQ_API_KEY:-}" && -n "${GOOGLE_API_KEY:-}" ]]; then
    BACKEND=api
  else
    BACKEND=none
  fi
fi

case "$BACKEND" in
  local)
    pip install -q torch transformers accelerate "qwen-vl-utils[decord]"
    python - <<'PY'
import torch
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"  cuda:{i}  {p.name}  {p.total_memory / 1e9:.1f} GB")
PY
    if [[ -n "$GPU" ]]; then
      DEVICE="cuda:${GPU}"; export CUDA_VISIBLE_DEVICES="$GPU"
    else
      DEVICE="auto"
    fi
    echo "  backend: local ($MODEL on $DEVICE)"
    ARGS=(--backend local --model "$MODEL" --device "$DEVICE")
    ;;
  api)
    pip install -q groq google-genai
    echo "  backend: api (Groq + Gemini)"
    ARGS=(--backend api)
    ;;
  none)
    echo "  backend: none -- rendering videos and timelines only."
    echo "  No GPU found and no API keys set. To generate AARs, either:"
    echo "    export GROQ_API_KEY=... GOOGLE_API_KEY=... && bash run.sh"
    echo "    or run this on a machine with a GPU."
    ARGS=(--no-llm)
    ;;
  *)
    echo "unknown BACKEND: $BACKEND" >&2; exit 1
    ;;
esac

echo
echo "=== 3/4  running pipeline ==="
python run_pipeline.py --layout "$LAYOUT" --n-trials "$N_TRIALS" --out "$OUT" "${ARGS[@]}"

echo
echo "=== 4/4  done ==="
echo "  $OUT/report.md      human-readable AARs"
echo "  $OUT/results.json   structured output"
echo "  $OUT/videos/        rendered gameplay mp4s"
echo "  $OUT/timelines/     event timelines fed to the model"
if [[ "$BACKEND" != "none" ]]; then
  echo
  echo "Next: python rate_aars.py --results $OUT/results.json"
fi
