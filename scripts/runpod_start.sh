#!/usr/bin/env bash
set -euo pipefail

SOURCE="${RUNPOD_SOURCE:-/workspace/input/sample.mp4}"
FACE_MODE="${FACE_MODE:-recognition}"
TRACKER_BACKEND="${TRACKER_BACKEND:-deepsort}"
CONFIDENCE="${CONFIDENCE:-0.5}"
MODEL_PATH="${MODEL_PATH:-yolov8n.pt}"
PORT="${PORT:-8000}"
EDGE_FACE_API="${EDGE_FACE_API:-}"

echo "Starting surveillance dashboard"
echo "  source: ${SOURCE}"
echo "  face mode: ${FACE_MODE}"
echo "  tracker: ${TRACKER_BACKEND}"
echo "  model: ${MODEL_PATH}"
echo "  port: ${PORT}"

ARGS=(
  "surveillance_live_service.py"
  "--source" "${SOURCE}"
  "--face-mode" "${FACE_MODE}"
  "--backend" "${TRACKER_BACKEND}"
  "--conf" "${CONFIDENCE}"
  "--model" "${MODEL_PATH}"
  "--host" "0.0.0.0"
  "--port" "${PORT}"
)

if [[ -n "${EDGE_FACE_API}" ]]; then
  ARGS+=("--edge-face-api" "${EDGE_FACE_API}")
fi

python "${ARGS[@]}"
