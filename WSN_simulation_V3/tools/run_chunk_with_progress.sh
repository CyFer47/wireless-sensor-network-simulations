#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  tools/run_chunk_with_progress.sh \
    --scale S7 \
    --seed-start 11 \
    --seed-end 20 \
    --output-subdir outputs_production_50seed_part11_20 \
    [--target-runs 2040] \
    [--min-free-gb 10] \
    [--poll-seconds 20]

Notes:
  - This is a wrapper around tools/run_production_v3_50seed.py.
  - It does not modify simulator code.
  - It prints a simple text progress bar based on output folder count.
USAGE
}

SCALE=""
SEED_START=""
SEED_END=""
OUTPUT_SUBDIR=""
TARGET_RUNS=2040
MIN_FREE_GB=10
POLL_SECONDS=20

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scale)
      SCALE="$2"; shift 2 ;;
    --seed-start)
      SEED_START="$2"; shift 2 ;;
    --seed-end)
      SEED_END="$2"; shift 2 ;;
    --output-subdir)
      OUTPUT_SUBDIR="$2"; shift 2 ;;
    --target-runs)
      TARGET_RUNS="$2"; shift 2 ;;
    --min-free-gb)
      MIN_FREE_GB="$2"; shift 2 ;;
    --poll-seconds)
      POLL_SECONDS="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2 ;;
  esac
done

if [[ -z "$SCALE" || -z "$SEED_START" || -z "$SEED_END" || -z "$OUTPUT_SUBDIR" ]]; then
  echo "Missing required arguments." >&2
  usage
  exit 2
fi

# Keep explicit scale mapping reliable for existing naming convention.
case "$SCALE" in
  S1) RUNS_DIR="runs/S1_50" ;;
  S2) RUNS_DIR="runs/S2_100" ;;
  S3) RUNS_DIR="runs/S3_200" ;;
  S4) RUNS_DIR="runs/S4_400" ;;
  S5) RUNS_DIR="runs/S5_800" ;;
  S6) RUNS_DIR="runs/S6_1600" ;;
  S7) RUNS_DIR="runs/S7_3200" ;;
  S8) RUNS_DIR="runs/S8_6400" ;;
  S9) RUNS_DIR="runs/S9_4500" ;;
  S10) RUNS_DIR="runs/S10_5000" ;;
  *) echo "Unsupported scale: $SCALE" >&2; exit 2 ;;
esac

OUT_DIR="${RUNS_DIR}/${OUTPUT_SUBDIR}"
mkdir -p "$OUT_DIR"

start_ts=$(date +%s)

echo "Starting chunk runner with progress bar"
echo "scale=${SCALE} seeds=${SEED_START}-${SEED_END} out=${OUTPUT_SUBDIR} target=${TARGET_RUNS} min_free_gb=${MIN_FREE_GB}"

python3 tools/run_production_v3_50seed.py \
  --scale "$SCALE" \
  --seed-start "$SEED_START" \
  --seed-end "$SEED_END" \
  --skip-existing \
  --output-subdir "$OUTPUT_SUBDIR" \
  --min-free-gb "$MIN_FREE_GB" \
  > >(tee /tmp/run_chunk_${SCALE}_${SEED_START}_${SEED_END}.log) 2>&1 &
runner_pid=$!

bar_width=40

render_bar() {
  local current="$1"
  local total="$2"
  if [[ "$total" -le 0 ]]; then
    total=1
  fi

  local pct=$(( current * 100 / total ))
  if [[ "$pct" -gt 100 ]]; then
    pct=100
  fi

  local filled=$(( current * bar_width / total ))
  if [[ "$filled" -gt "$bar_width" ]]; then
    filled=$bar_width
  fi
  local empty=$(( bar_width - filled ))

  local bar_filled bar_empty
  bar_filled=$(printf '%*s' "$filled" '' | tr ' ' '#')
  bar_empty=$(printf '%*s' "$empty" '' | tr ' ' '.')

  printf '\r[%s%s] %3d%% (%d/%d)' "$bar_filled" "$bar_empty" "$pct" "$current" "$total"
}

while kill -0 "$runner_pid" 2>/dev/null; do
  count=$(find "$OUT_DIR" -maxdepth 1 -type d -name 'run_campaign_v3_*' | wc -l)
  render_bar "$count" "$TARGET_RUNS"
  sleep "$POLL_SECONDS"
done

wait "$runner_pid"
runner_rc=$?

final_count=$(find "$OUT_DIR" -maxdepth 1 -type d -name 'run_campaign_v3_*' | wc -l)
render_bar "$final_count" "$TARGET_RUNS"

end_ts=$(date +%s)
elapsed=$(( end_ts - start_ts ))
printf '\nDone. exit_code=%d elapsed=%ss final_count=%d target=%d\n' "$runner_rc" "$elapsed" "$final_count" "$TARGET_RUNS"

exit "$runner_rc"
