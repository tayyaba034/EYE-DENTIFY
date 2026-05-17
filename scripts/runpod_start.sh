#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Install ngrok inside the pod (first run only)
# =============================================================================
if ! command -v ngrok &> /dev/null; then
    echo "Installing ngrok..."
    curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list
    apt-get update && apt-get install ngrok -y
fi

# =============================================================================
# Authenticate ngrok (set NGROK_AUTHTOKEN as a RunPod env variable)
# =============================================================================
if [[ -z "${NGROK_AUTHTOKEN:-}" ]]; then
    echo "WARNING: NGROK_AUTHTOKEN not set. ngrok tunnel will have limited functionality."
else
    ngrok config add-authtoken "${NGROK_AUTHTOKEN}"
fi

# =============================================================================
# Start ngrok tunnel in background
# =============================================================================
PORT="${PORT:-8000}"
if [[ -n "${NGROK_DOMAIN:-}" ]]; then
    echo "Starting ngrok tunnel on domain: ${NGROK_DOMAIN}"
    ngrok http "${PORT}" --domain="${NGROK_DOMAIN}" --log=stdout &
    NGROK_PID=$!
    
    # Wait for tunnel to be ready
    sleep 4
    
    echo ""
    echo "============================================"
    echo "ngrok Tunnel Ready"
    echo "============================================"
    echo "ESP32 should POST frames to:"
    echo "  https://${NGROK_DOMAIN}/api/esp32/frame"
    echo ""
    echo "Dashboard:"
    echo "  https://${NGROK_DOMAIN}/"
    echo "============================================"
    echo ""
fi

# =============================================================================
# Configure environment variables
# =============================================================================
SOURCE="${RUNPOD_SOURCE:-/workspace/input/sample.mp4}"
FACE_MODE="${FACE_MODE:-none}"
TRACKER_BACKEND="${TRACKER_BACKEND:-deepsort}"
CONFIDENCE="${CONFIDENCE:-0.5}"
MODEL_PATH="${MODEL_PATH:-yolov8n.pt}"
EDGE_FACE_API="${EDGE_FACE_API:-}"

echo "Starting surveillance dashboard"
echo "  source: ${SOURCE}"
echo "  face mode: ${FACE_MODE}"
echo "  tracker: ${TRACKER_BACKEND}"
echo "  model: ${MODEL_PATH}"
echo "  port: ${PORT}"

# =============================================================================
# Start the pipeline service
# =============================================================================
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
