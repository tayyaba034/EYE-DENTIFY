#!/usr/bin/env bash
# scripts/cloud_start.sh
# Generic startup script for Cloud VMs (GCP, AWS, RunPod)
set -euo pipefail

# Environment Variables with Defaults
SOURCE="${RUNPOD_SOURCE:-${SOURCE:-0}}"
FACE_MODE="${FACE_MODE:-recognition}"
TRACKER_BACKEND="${TRACKER_BACKEND:-deepsort}"
CONFIDENCE="${CONFIDENCE:-0.5}"
MODEL_PATH="${MODEL_PATH:-yolov8n.pt}"
PORT="${PORT:-8000}"
EDGE_FACE_API="${EDGE_FACE_API:-}"
ESP32_MODE="${ESP32_MODE:-0}"

echo "========================================"
echo "   EYE-DENTIFY CLOUD DEPLOYMENT"
echo "========================================"
echo "  ESP32 Mode:   ${ESP32_MODE}"
echo "  Source:       ${SOURCE}"
echo "  Face Mode:    ${FACE_MODE}"
echo "  Tracker:      ${TRACKER_BACKEND}"
echo "  Model:        ${MODEL_PATH}"
echo "  Port:         ${PORT}"
echo "========================================"

ARGS=(
  "surveillance_live_service.py"
  "--face-mode" "${FACE_MODE}"
  "--backend" "${TRACKER_BACKEND}"
  "--conf" "${CONFIDENCE}"
  "--model" "${MODEL_PATH}"
  "--host" "0.0.0.0"
  "--port" "${PORT}"
)

# Toggle ESP32 mode vs Source mode
if [[ "${ESP32_MODE}" == "1" || "${ESP32_MODE}" == "true" ]]; then
  echo "[INFO] Enabling ESP32 ingestion mode."
  ARGS+=("--esp32-mode")
else
  echo "[INFO] Using standard source: ${SOURCE}"
  ARGS+=("--source" "${SOURCE}")
fi

if [[ -n "${EDGE_FACE_API}" ]]; then
  ARGS+=("--edge-face-api" "${EDGE_FACE_API}")
fi

python "${ARGS[@]}"
