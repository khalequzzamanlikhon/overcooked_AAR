#!/usr/bin/env bash
# Study v2, start to finish, in the background. Everything goes to a log file.
#
#   bash run_study.sh                     # start; prints the log path and returns
#   tail -f logs/latest.log               # watch it
#   bash run_study.sh --status            # is it running, which step is it on
#   bash run_study.sh --stop              # stop it (finished work is kept; rerun resumes)
#
# Options, as environment variables:
#   MODELS="qwen25vl7b_4bit qwen25vl7b_bf16 qwen3vl8b_bf16"   which models (tags from aar/config.py)
#   PHASES="setup rescore probe_build smoke pilot probe all analyze variance"   which steps
#   GPUS=0,1        the GPUs it may use. 4-bit goes on the one with most free memory,
#                   bf16 is spread over all of them.
#   EPISODES=all    for the `all` phase: all | N
#   SEEDS="1 2 3"   for the variance phase
#
# Every step resumes: finished episodes, conditions and probe items are skipped
# on a rerun, so after a crash or --stop just run it again.
#
# Steps:
#   setup        install requirements, run the tests
#   rescore      re-score both pilot runs with the study-v2 scorer (no GPU)
#   probe_build  build the perception-probe items (no GPU)
#   smoke        per model: 1 minute of 1 episode, every condition, and 20 probe items;
#                a model that fails here is skipped for the rest
#   pilot        per model: the pilot's 15 episodes, every condition
#   probe        per model: every probe item in every variant
#   all          per model: all 76 episodes (the 15 are already done)
#   analyze      metrics with CIs per run, the probe tables, the cross-model summary
#   variance     per model: pilot's 15, telemetry + video_dense, sampled decoding, 3 seeds

set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")"

PIDFILE=logs/study.pid

if [[ "${1:-}" == "--status" ]]; then
  if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "running (pid $(cat $PIDFILE)), log: $(readlink -f logs/latest.log)"
    grep -E "^=+ |STEP|FAILED|done in" logs/latest.log | tail -n 5
  else
    echo "not running"; [[ -e logs/latest.log ]] && echo "last log: $(readlink -f logs/latest.log)"
  fi
  exit 0
fi
if [[ "${1:-}" == "--stop" ]]; then
  if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    kill -- -"$(cat $PIDFILE)" 2>/dev/null || kill "$(cat $PIDFILE)"
    echo "stopped pid $(cat $PIDFILE)"; rm -f $PIDFILE
  else
    echo "not running"
  fi
  exit 0
fi

# detach: rerun this script in its own session with all output going to the log
if [[ -z "${_STUDY_CHILD:-}" ]]; then
  mkdir -p logs
  if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "already running (pid $(cat $PIDFILE)); see logs/latest.log or use --stop"; exit 1
  fi
  LOG="logs/study_$(date +%Y-%m-%d_%H%M%S).log"
  ln -sfn "$(basename "$LOG")" logs/latest.log
  _STUDY_CHILD=1 setsid nohup bash "$0" "$@" >"$LOG" 2>&1 </dev/null &
  echo $! >$PIDFILE
  echo "started in the background (pid $!)"
  echo "  log:    $LOG   (tail -f logs/latest.log)"
  echo "  status: bash run_study.sh --status"
  echo "  stop:   bash run_study.sh --stop"
  exit 0
fi

# ---------------------------------------------------------------- the run itself

MODELS="${MODELS:-qwen25vl7b_4bit qwen25vl7b_bf16 qwen3vl8b_bf16}"
PHASES="${PHASES:-setup rescore probe_build smoke pilot probe all analyze variance}"
GPUS="${GPUS:-0,1}"
EPISODES="${EPISODES:-all}"
SEEDS="${SEEDS:-1 2 3}"
ROOT=results/v2
VIDEOS=$ROOT/videos

export SDL_VIDEODRIVER=dummy TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source .venv/bin/activate

FAILED=()
SKIP_MODELS=" "
T_START=$(date +%s)

log() { echo "$(date '+%F %T') $*"; }
has_phase() { [[ " $PHASES " == *" $1 "* ]]; }

step() {  # step <name> <command...>: run it, time it, keep going if it fails
  local name=$1; shift
  log "STEP $name: $*"
  local t0=$(date +%s)
  "$@"
  local rc=$?
  local dt=$(( $(date +%s) - t0 ))
  if [[ $rc -ne 0 ]]; then
    log "FAILED $name (exit $rc) after $((dt / 60)) min"
    FAILED+=("$name")
  else
    log "done in $((dt / 60)) min: $name"
  fi
  return $rc
}

model_id()  { python -c "from aar.config import MODELS; print(MODELS['$1'][0])"; }
is_4bit()   { python -c "from aar.config import MODELS; print(int(MODELS['$1'][1]))"; }

# 4-bit: the allowed GPU with the most free memory. bf16: all allowed GPUs, spread by accelerate.
with_gpu() {  # with_gpu <tag> <command...>
  local tag=$1; shift
  local flags
  if [[ $(is_4bit "$tag") == 1 ]]; then
    local best
    best=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits |
      awk -F', ' -v allow=",$GPUS," 'index(allow, ","$1",") {print $2, $1}' | sort -rn | head -n1 | cut -d' ' -f2)
    log "  $tag on GPU $best ($(nvidia-smi --query-gpu=memory.free --format=csv,noheader -i "$best") free)"
    CUDA_VISIBLE_DEVICES=$best "$@" --model "$(model_id "$tag")" --device cuda:0
  else
    log "  $tag on GPUs $GPUS (bf16, spread)"
    CUDA_VISIBLE_DEVICES=$GPUS "$@" --model "$(model_id "$tag")" --device auto --bf16
  fi
}

log "========== study v2 =========="
log "models: $MODELS"
log "phases: $PHASES"
log "gpus: $GPUS   episodes: $EPISODES   git: $(git rev-parse --short HEAD) $(git status --porcelain | grep -q . && echo '(dirty)')"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

if has_phase setup; then
  log "========== setup =========="
  step pip pip install -q -r requirements.txt
  step tests python -m pytest tests -q
fi

if has_phase rescore; then
  log "========== re-score the pilots with the v2 scorer =========="
  for pilot in results/pilot_2026-09 results/pilot_2026-09b; do
    step "rescore $(basename $pilot)" python analyze.py --run "$pilot" --no-legacy --out "$ROOT/rescored/$(basename $pilot)"
  done
fi

if has_phase probe_build; then
  log "========== build the probe =========="
  if [[ -s probes/probe_v1.jsonl ]]; then
    log "probes/probe_v1.jsonl exists; keeping it (delete it to rebuild)"
  else
    step probe_build python scripts/probe_build.py --out probes/probe_v1.jsonl
  fi
fi

if has_phase smoke; then
  log "========== smoke tests =========="
  for tag in $MODELS; do
    ok=1
    step "smoke pipeline $tag" with_gpu "$tag" python run_pipeline.py --episodes 1 --max-segments 1 \
      --out "$ROOT/smoke/$tag" --video-cache "$VIDEOS" || ok=0
    if [[ $ok == 1 ]]; then
      step "smoke probe $tag" with_gpu "$tag" python scripts/probe_run.py --out "$ROOT/smoke/$tag/probe" \
        --variants video_main text --limit 20 || ok=0
    fi
    if [[ $ok == 0 ]]; then
      log "!! $tag failed its smoke test; skipping it for the rest of the run"
      SKIP_MODELS+="$tag "
    fi
  done
fi

run_models() { for tag in $MODELS; do [[ "$SKIP_MODELS" == *" $tag "* ]] || echo "$tag"; done; }

if has_phase pilot; then
  log "========== the pilot's 15 episodes, every condition =========="
  for tag in $(run_models); do
    step "pilot $tag" with_gpu "$tag" python run_pipeline.py --episodes pilot --out "$ROOT/$tag" --video-cache "$VIDEOS"
    step "analyze $tag (15)" python analyze.py --run "$ROOT/$tag"
  done
fi

if has_phase probe; then
  log "========== perception probe =========="
  for tag in $(run_models); do
    step "probe $tag" with_gpu "$tag" python scripts/probe_run.py --out "$ROOT/probe/$tag"
  done
fi

if has_phase all; then
  log "========== all episodes ($EPISODES), every condition =========="
  for tag in $(run_models); do
    step "all $tag" with_gpu "$tag" python run_pipeline.py --episodes "$EPISODES" --out "$ROOT/$tag" --video-cache "$VIDEOS"
  done
fi

if has_phase analyze; then
  log "========== analysis =========="
  for tag in $(run_models); do
    [[ -f $ROOT/$tag/results.json ]] && step "analyze $tag" python analyze.py --run "$ROOT/$tag"
  done
  [[ -d $ROOT/probe ]] && step "analyze probe" python scripts/analyze_probe.py --probe "$ROOT/probe"
  step "summary" python scripts/analyze_study.py --root "$ROOT"
fi

if has_phase variance; then
  log "========== variance: sampled decoding, seeds $SEEDS =========="
  for tag in $(run_models); do
    for seed in $SEEDS; do
      out="$ROOT/variance/${tag}_seed$seed"
      step "variance $tag seed $seed" with_gpu "$tag" python run_pipeline.py --episodes pilot \
        --conditions telemetry video_dense --do-sample --seed "$seed" --out "$out" --video-cache "$VIDEOS" &&
        step "analyze variance $tag seed $seed" python analyze.py --run "$out" --no-legacy
    done
  done
  step "summary" python scripts/analyze_study.py --root "$ROOT"
fi

log "========== finished in $(( ($(date +%s) - T_START) / 3600 )) h $(( ($(date +%s) - T_START) % 3600 / 60 )) min =========="
if [[ ${#FAILED[@]} -gt 0 ]]; then
  log "failed steps (rerun to resume them):"
  for f in "${FAILED[@]}"; do log "  - $f"; done
fi
log "results: $ROOT/SUMMARY.md, $ROOT/<model>/metrics_v2.md, $ROOT/probe/probe_summary.md"
log "next, the blind human rating (by hand, one file per rater):"
log "  python rate_aars.py --run $ROOT/qwen3vl8b_bf16 --rater <name> --pairs telemetry:video_dense,video_dense:video_log --likert"
rm -f "$PIDFILE"
