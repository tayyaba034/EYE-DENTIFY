# RunPod Hourly Deployment

This project should run on a RunPod **On-Demand GPU Pod** because the live Flask dashboard is a continuously running service. Do not use `--source 0` on RunPod unless a camera is physically attached to the Pod. Use an uploaded video file, RTSP stream, or HTTP camera stream.

## 1. Build or Upload

Use `Dockerfile.runpod` for a GPU image:

```bash
docker build -f Dockerfile.runpod -t surveillance-runpod .
```

Push that image to Docker Hub/GHCR, then select it as a custom image in RunPod. If you prefer to clone the repo inside a PyTorch template Pod, follow the manual commands below instead.

## 2. RunPod Pod Settings

- Pod type: On-Demand GPU
- GPU: RTX 3090, RTX 4090, A4000, A5000, or better
- Disk: 50-100 GB
- HTTP port: `8000/http`
- Container disk path: `/app`
- Optional persistent data path: `/workspace`

The dashboard URL will look like:

```text
https://<pod-id>-8000.proxy.runpod.net
```

## 3. Runtime Environment

Set these environment variables in the Pod:

```text
RUNPOD_SOURCE=/workspace/input/sample.mp4
FACE_MODE=recognition
TRACKER_BACKEND=deepsort
MODEL_PATH=yolov8n.pt
CONFIDENCE=0.5
PORT=8000
```

### ngrok Tunnel Configuration (Optional but Recommended for ESP32)

To enable external ESP32 devices to POST frames to your RunPod, add these environment variables:

```text
NGROK_AUTHTOKEN=<your-ngrok-auth-token>
NGROK_DOMAIN=<your-ngrok-free-domain>
```

**How to set up ngrok:**

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Get your **Auth Token** from the dashboard
3. Reserve a free domain name (e.g., `paprika-impure-salvation.ngrok-free.dev`)
4. Set `NGROK_AUTHTOKEN` and `NGROK_DOMAIN` in RunPod pod environment

When the Pod starts, `scripts/runpod_start.sh` will:
- Install ngrok on first run
- Authenticate with your token
- Open an HTTP tunnel to your dashboard
- Print the public ESP32 ingestion endpoint:

```
ESP32 should POST frames to:
  https://<NGROK_DOMAIN>/api/esp32/frame
```

For RTSP camera, use:

```text
RUNPOD_SOURCE=rtsp://username:password@camera-ip:554/stream1
```

For edge face input, also set:

```text
EDGE_FACE_API=http://your-edge-device/api/path
```

Add Supabase values only as RunPod environment variables. Do not bake `.env` into the image.

## 4. Manual Pod Setup Without Docker

Start from an official RunPod PyTorch/CUDA template, then run:

```bash
cd /workspace
git clone <your-repo-url> surveillance-pipeline
cd surveillance-pipeline
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install torch==2.2.2+cu121 torchvision==0.17.2+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install onnxruntime-gpu==1.17.3
grep -viE "^torch([=<>! ].*)?$|^torchvision([=<>! ].*)?$|^onnxruntime([=<>! ].*)?$" requirements-deployment.txt > requirements-runpod-filtered.txt
pip install -r requirements-runpod-filtered.txt
```

Upload a video to `/workspace/input/sample.mp4`, then start:

```bash
RUNPOD_SOURCE=/workspace/input/sample.mp4 PORT=8000 bash scripts/runpod_start.sh
```

Or run an RTSP source:

```bash
RUNPOD_SOURCE="rtsp://username:password@camera-ip:554/stream1" PORT=8000 bash scripts/runpod_start.sh
```

## 5. Test Endpoints

Open:

```text
https://<pod-id>-8000.proxy.runpod.net/
```

Useful checks:

```text
/api/state
/api/frame.jpg
/api/stream.mjpg
/api/alerts
```

## 6. Stop Hourly Billing

When finished, stop or terminate the Pod in RunPod. If you need files to survive between Pods, attach a RunPod Network Volume and keep videos/models under `/workspace`.
