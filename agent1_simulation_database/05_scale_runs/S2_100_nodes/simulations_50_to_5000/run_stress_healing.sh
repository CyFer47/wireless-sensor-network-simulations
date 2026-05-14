#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/cyfer/FYP/WSN_simulation"
SCALE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_ROOT="$ROOT/01_core_source"
TOOL="$ROOT/02_tools/run_from_spec.py"
CATEGORY="stress_healing"
SCALE_TAG="$(basename "$SCALE_DIR" | cut -d_ -f1)"

SPEC="$(find "$SCALE_DIR/runspecs/$CATEGORY" -maxdepth 1 -type f -name "*_${SCALE_TAG}_*.json" | sort | head -n 1)"
MAP_DIR="$(find "$SCALE_DIR/maps" -mindepth 1 -maxdepth 2 -type d -name "map_${SCALE_TAG}_*" | sort | head -n 1)"
OUT_DIR="$SCALE_DIR/local_outputs"

if [[ -z "${SPEC:-}" || ! -f "$SPEC" ]]; then
  echo "No runspec found for scale $SCALE_TAG in $SCALE_DIR/runspecs/$CATEGORY" >&2
  exit 1
fi
if [[ -z "${MAP_DIR:-}" || ! -d "$MAP_DIR" ]]; then
  echo "No map directory found for scale $SCALE_TAG in $SCALE_DIR/maps" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "Running scale: $SCALE_TAG"
echo "Category: $CATEGORY"
echo "Spec: $SPEC"
echo "Map: $MAP_DIR"
echo "Outputs: $OUT_DIR"
echo "Next import step: python3 $ROOT/03_database/import_export/import_run_to_postgres.py <run_dir>"
python3 "$TOOL" --spec "$SPEC" --map "$MAP_DIR" --ns3-root "$NS3_ROOT" --output-root "$OUT_DIR" "$@"
