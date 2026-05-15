# AWS Demo Deployment Guide — Multi-Camera, 1 Month, Single Instance

## What This Gives You

- One EC2 **g4dn.xlarge** instance with NVIDIA T4 GPU (~$95–174/month)
- Full pipeline running at **20–30 FPS** — YOLOv8, DeepSORT, InsightFace, all GPU-accelerated
- Multi-camera support — round-robin or priority-failover between N cameras
- **Sentinel Command dashboard** served directly from the same instance
- Live MJPEG stream with full pipeline overlay (bounding boxes, track IDs, fusion scores)
- Per-camera individual streams at `/api/stream/cam_N.mjpg`
- Supabase free tier for alert persistence
- Docker-based — reproducible, easy to tear down after demo

---

## Architecture

```
Your Cameras (RTSP / video files / webcam)
         ↓
   EC2 g4dn.xlarge (GPU Docker)
   multicam_live_service.py  ←  full pipeline with GPU inference
         ↓
   /                         ← Sentinel Command dashboard (your web app)
   /api/state                ← dashboard polls this every 2.5s
   /api/stream.mjpg          ← active camera MJPEG stream (live overlay)
   /api/stream/cam_1.mjpg    ← per-camera streams
   /api/alerts               ← alert history
         ↓
   Supabase (free tier) ← alerts stored here
```

---

## Instance Options

| Instance | GPU | vCPU | RAM | FPS (estimate) | Cost/month (on-demand) |
|---|---|---|---|---|---|
| **g4dn.xlarge** | T4 16GB | 4 | 16 GB | 20–30 FPS | ~$380 |
| **g4dn.xlarge** (1yr reserved) | T4 16GB | 4 | 16 GB | 20–30 FPS | **~$170** |
| t3.medium (CPU only) | none | 2 | 4 GB | 3–8 FPS | ~$30 |

For a **live streaming demo with the full web app and real-time overlay**, use **g4dn.xlarge**. The T4 GPU handles YOLOv8, DeepSORT appearance embeddings, and InsightFace all simultaneously at real-time FPS.

---

## Cost Breakdown (1 Month Demo — GPU)

| Item | Cost |
|---|---|
| EC2 g4dn.xlarge on-demand (720 hrs) | ~$380 |
| EC2 g4dn.xlarge **1-year reserved** (recommended) | **~$170** |
| EBS gp3 30 GB root volume | ~$2.40 |
| Elastic IP (attached, running) | $0.00 |
| Data transfer out (dashboard + stream, ~20 GB) | ~$1.80 |
| Supabase free tier | $0.00 |
| **Total (reserved)** | **~$174/month** |
| **Total (on-demand, stop when not demoing 12hr/day)** | **~$95/month** |

> Stopping the instance when not demoing cuts on-demand cost roughly in half.
> You only pay for EBS (~$2.40/month) while stopped.

---

## Pre-Deployment Checklist

- [ ] AWS account with billing enabled
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Docker installed locally
- [ ] Your `.env` file has Supabase keys (or leave them blank for local-only)
- [ ] Camera sources identified (RTSP URLs, video file paths, or `0`/`1` for webcam)

---

## Step 1 — Prepare Your .env for Deployment

Create a `.env.deploy` file (never commit this):

```bash
# Supabase (optional — leave blank to disable remote alerts)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
SUPABASE_ALERTS_TABLE=alerts

# Pipeline behaviour
ENABLE_REMOTE_ALERTS=0
API_AUTH_REQUIRED=0
KMP_DUPLICATE_LIB_OK=TRUE

# Multi-cam settings (override at runtime via CLI args, but set defaults here)
CAMERA_SOURCES=0
FACE_MODE=none
TRACKER_BACKEND=bytetrack
PRIORITY_FAILOVER=
MATCH_SIGNAL=track
CONF_THRESHOLD=0.5
```

> Set `ENABLE_REMOTE_ALERTS=1` and fill in Supabase keys if you want alerts
> to persist to the database and show in the dashboard alert panel.

---

## Step 2 — Launch EC2 Instance (g4dn.xlarge)

### AWS Console

1. Go to EC2 → Launch Instance
2. Name: `surveillance-demo`
3. AMI: **Ubuntu Server 22.04 LTS**
4. Instance type: **g4dn.xlarge** (4 vCPU, 16 GB RAM, 1× T4 GPU)
5. Key pair: create or select one, download the `.pem` file
6. Security group — add these inbound rules:
   - SSH: port 22, source = your IP only
   - Custom TCP: port 8000, source = your IP (or 0.0.0.0/0 for open demo)
7. Storage: **30 GB gp3** (the CUDA base image is large)
8. Launch

### AWS CLI

```bash
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type g4dn.xlarge \
  --key-name YOUR_KEY_PAIR_NAME \
  --security-group-ids YOUR_SG_ID \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=surveillance-demo}]' \
  --count 1
```

> **Note:** g4dn instances require your AWS account to have GPU instance limits approved.
> If you get a limit error, request a quota increase in EC2 → Limits for `g4dn.xlarge`
> (usually approved within minutes for 1 instance).

---

## Step 3 — Install Docker + NVIDIA Container Toolkit on the Instance

SSH into the instance:

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

Install Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker
```

Install NVIDIA Container Toolkit (this is what lets Docker see the GPU):

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify GPU is visible to Docker:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
# Should print your T4 GPU info
```

---

## Step 4 — Copy Your Project to EC2

### Option A: rsync (recommended, excludes large files)

From your local machine:

```bash
rsync -avz \
  --exclude '.venv' \
  --exclude 'height_estimation_module/venv310_new' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'runtime/artifacts' \
  --exclude '.git' \
  -e "ssh -i your-key.pem" \
  . ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/pipeline/
```

### Option B: git clone (if repo is on GitHub)

```bash
# On the EC2 instance
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /home/ubuntu/pipeline
```

> If using git, make sure `.env` is in `.gitignore` and copy it separately:
> ```bash
> scp -i your-key.pem .env.deploy ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/pipeline/.env
> ```

---

## Step 5 — Build and Run

On the EC2 instance:

```bash
cd /home/ubuntu/pipeline

# Copy your deploy env file
cp .env.deploy .env

# Build the GPU Docker image (takes 10-15 min first time — CUDA base is large)
docker compose -f docker-compose.gpu.yml build

# Run with RTSP cameras
CAMERA_SOURCES="rtsp://cam1/stream,rtsp://cam2/stream" \
docker compose -f docker-compose.gpu.yml up -d

# Run with priority-failover (check cam1 first, fall back to cam2)
CAMERA_SOURCES="rtsp://cam1/stream,rtsp://cam2/stream" \
PRIORITY_FAILOVER=true \
MATCH_SIGNAL=track \
docker compose -f docker-compose.gpu.yml up -d

# Run with video files for demo
CAMERA_SOURCES="/app/videos/demo1.mp4,/app/videos/demo2.mp4" \
docker compose -f docker-compose.gpu.yml up -d

# Watch logs
docker compose -f docker-compose.gpu.yml logs -f
```

---

## Step 6 — Verify It's Working

```bash
# Health check
curl http://YOUR_EC2_PUBLIC_IP:8000/live
# Expected: {"status": "alive"}

# Readiness check (wait up to 90s for models to load)
curl http://YOUR_EC2_PUBLIC_IP:8000/ready
# Expected: {"ready": true, "camera_count": 2, "active_camera_id": "cam_1", ...}

# Pipeline state
curl http://YOUR_EC2_PUBLIC_IP:8000/api/state | python3 -m json.tool | head -40
# Expected: {"status": "running", "cameras": [...], "active_camera_id": "cam_1"}

# Verify GPU is being used inside the container
docker exec -it pipeline-multicam-pipeline-gpu-1 \
  python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"
# Expected: CUDA available: True  /  GPU: Tesla T4
```

Open the dashboard in your browser:
```
http://YOUR_EC2_PUBLIC_IP:8000
```

You should see:
- **Live feed panel** — MJPEG stream with bounding boxes, track IDs, fusion scores overlaid
- **Feed status** — shows `2 cameras · Parallel · Active: cam_1` (or failover mode)
- **Stage summary** — detection count, track count, fusion results
- **Track table** — live entity register with face score, clothing color, height
- **Alert queue** — fires when fusion + temporal validation threshold is crossed

---

## Step 7 — Live Stream URLs

The dashboard streams automatically. You can also open these directly in any browser or VLC:

| URL | What it shows |
|---|---|
| `http://IP:8000/api/stream.mjpg` | Active camera (auto-switches in failover mode) |
| `http://IP:8000/api/stream/cam_1.mjpg` | Camera 1 only |
| `http://IP:8000/api/stream/cam_2.mjpg` | Camera 2 only |
| `http://IP:8000/api/frame.jpg` | Single snapshot of active camera |

In VLC: Media → Open Network Stream → paste the URL.

---

## Camera Source Reference

| Source type | Example value for `--sources` |
|---|---|
| Local webcam (first) | `0` |
| Local webcam (second) | `1` |
| Video file | `/app/videos/demo.mp4` |
| RTSP IP camera | `rtsp://admin:pass@192.168.1.100:554/stream` |
| HTTP MJPEG stream | `http://192.168.1.100:8080/video` |
| Two cameras | `0,1` |
| Two RTSP streams | `rtsp://cam1/stream,rtsp://cam2/stream` |

> For video files, copy them into the project folder before rsync so they
> end up at `/app/videos/` inside the container, or mount a volume.

---

## Switching Modes

### Parallel mode (default)
Both cameras processed every cycle. Active camera for the stream = first running camera.

```bash
CAMERA_SOURCES="0,1" \
docker compose -f docker-compose.gpu.yml up -d
```

### Priority-failover mode
Check cam_1 first. If it has a confirmed track, use it and skip cam_2.
If cam_1 has nothing, process cam_2.

```bash
CAMERA_SOURCES="rtsp://entrance/stream,rtsp://corridor/stream" \
PRIORITY_FAILOVER=true \
MATCH_SIGNAL=track \
docker compose -f docker-compose.gpu.yml up -d
```

### Alert-based failover
Only switch active camera when an alert fires on it.

```bash
CAMERA_SOURCES="rtsp://entrance/stream,rtsp://corridor/stream" \
PRIORITY_FAILOVER=true \
MATCH_SIGNAL=alert \
docker compose -f docker-compose.gpu.yml up -d
```

---

## Stopping and Restarting

```bash
# Stop the container (instance keeps running, no compute charge lost)
docker compose -f docker-compose.gpu.yml down

# Restart with different sources
CAMERA_SOURCES="new_source1,new_source2" \
docker compose -f docker-compose.gpu.yml up -d

# View live logs
docker compose -f docker-compose.gpu.yml logs -f --tail=100

# Check GPU + CPU usage inside container
docker stats
docker exec -it pipeline-multicam-pipeline-gpu-1 nvidia-smi
```

---

## Cost Control — Stop Instance When Not Demoing

If you only need the demo running during specific hours, stop the instance
when not in use. You only pay for compute while it's running.

```bash
# Get your instance ID
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=surveillance-demo" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text

# Stop (no compute charge while stopped, only EBS storage ~$1.60/month)
aws ec2 stop-instances --instance-ids i-XXXXXXXXXXXXXXXXX

# Start again
aws ec2 start-instances --instance-ids i-XXXXXXXXXXXXXXXXX

# Get new public IP after start (it changes unless you use Elastic IP)
aws ec2 describe-instances \
  --instance-ids i-XXXXXXXXXXXXXXXXX \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text
```

> To keep a fixed IP: allocate an Elastic IP and associate it with the instance.
> Cost: $0 while instance is running, $0.005/hr while stopped.

---

## Troubleshooting

**Container exits immediately:**
```bash
docker compose -f docker-compose.gpu.yml logs multicam-pipeline-gpu
```
Most common cause: camera source can't be opened. Check `CAMERA_SOURCES` value.

**`/ready` returns `{"ready": false}`:**
- Pipeline is still initializing — models take 30–90s to load on first start.
- Check logs for CUDA or model file errors.

**GPU not detected inside container:**
```bash
# Confirm nvidia-container-toolkit is working
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
# If this fails, re-run: sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```

**CUDA out of memory:**
- T4 has 16 GB VRAM — very unlikely with this pipeline
- If it happens: reduce `CONF_THRESHOLD=0.65` to detect fewer people per frame

**RTSP stream not connecting:**
```bash
docker exec -it pipeline-multicam-pipeline-gpu-1 \
  python -c "import cv2; cap=cv2.VideoCapture('rtsp://YOUR_URL'); print('opened:', cap.isOpened())"
```

**Dashboard shows stale data / empty panels:**
- Check `/ready` — if `frame_age_seconds` > 10, the pipeline loop is stalled
- Check logs for Python exceptions in the inference loop

**Low FPS despite GPU:**
- Confirm GPU is actually being used: `docker exec ... nvidia-smi` should show memory usage
- If CUDA is not available, torch fell back to CPU — check the `torch.cuda.is_available()` command from Step 6

---

## Cleanup (After Demo)

```bash
# Terminate instance (permanent — deletes everything)
aws ec2 terminate-instances --instance-ids i-XXXXXXXXXXXXXXXXX

# Release Elastic IP if you allocated one
aws ec2 release-address --allocation-id eipalloc-XXXXXXXXXXXXXXXXX
```

Total cleanup takes 2 minutes and stops all charges.
