# ESP32 Integration: Quick Reference & Code Templates

## ⚠️ IMPORTANT: Pipeline Runs on CLOUD ONLY - Not on ESP32

**Remember:** ESP32 is ONLY for streaming MJPEG video. ALL processing happens on the cloud.

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| **OV2640 Camera** | ESP32 (Edge) | Capture frames |
| **MJPEG Encoder** | ESP32 (Edge) | Encode to MJPEG |
| **HTTP Server** | ESP32 (Edge) | Stream video |
| **MJPEGStreamReceiver** | CLOUD | Decode MJPEG |
| **PersonDetector** | CLOUD | Detect people (YOLOv8) |
| **MultiObjectTracker** | CLOUD | Track people (DeepSORT) |
| **FaceExtractor** | CLOUD | Identify faces |
| **FusionEngine** | CLOUD | Combine signals |
| **AlertDecision** | CLOUD | Make decisions |
| **Database** | CLOUD (Supabase) | Store alerts |

---

## Quick Architecture Diagram

```
ESP32 Camera #1          ESP32 Camera #2
    (Hardware)              (Hardware)
     MJPEG Stream           MJPEG Stream
         ↓                      ↓
      WiFi (MJPEG-HTTP)     WiFi (MJPEG-HTTP)
         ↓                      ↓
    MJPEGStreamReceiver    MJPEGStreamReceiver
         ↓                      ↓
    ESP32CameraManager (Orchestrator)
         ↓
    MultiCameraESP32Pipeline
    ├─ PersonDetector (×2)
    ├─ MultiObjectTracker (×2)
    ├─ FaceExtractor
    ├─ Fusion
    └─ Alert Decision
         ↓
    Flask API Server (Port 8080)
         ↓
    [Web Dashboard, Mobile App, Alerts]
```

---

## File Structure to Create

```
esp32_stream_adapter/
├── __init__.py
├── config.py
├── mjpeg_receiver.py          # MJPEG decoder
├── frame_processor.py         # Frame preprocessing
├── esp32_manager.py           # Multi-camera orchestrator
├── requirements.txt
└── tests/
    ├── test_mjpeg_receiver.py
    └── test_esp32_manager.py

surveillance_esp32_pipeline.py  # Main pipeline orchestrator
esp32_api_server.py            # Flask API server
esp32_config.json              # Configuration file
Dockerfile.esp32               # Docker container
```

---

## Code Templates

### 1. `esp32_stream_adapter/__init__.py`

```python
"""ESP32 Stream Adapter - MJPEG stream receiver and processing."""

__version__ = "0.1.0"

from esp32_stream_adapter.mjpeg_receiver import MJPEGStreamReceiver
from esp32_stream_adapter.esp32_manager import ESP32CameraManager

__all__ = [
    "MJPEGStreamReceiver",
    "ESP32CameraManager",
]
```

### 2. `esp32_stream_adapter/config.py`

```python
"""Configuration for ESP32 stream adapter."""

import os
from functools import lru_cache

# MJPEG Stream Settings
MJPEG_BOUNDARY = b"--123456789000000000000"
STREAM_TIMEOUT = int(os.getenv("STREAM_TIMEOUT", "10"))
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))

# Frame Processing
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "600"))
STREAM_FPS = int(os.getenv("STREAM_FPS", "10"))
FRAME_INTERVAL_MS = int(1000 / STREAM_FPS)  # milliseconds

# Buffer Settings
FRAME_BUFFER_SIZE = int(os.getenv("FRAME_BUFFER_SIZE", "1000000"))  # 1MB
MAX_JPEG_SIZE = int(os.getenv("MAX_JPEG_SIZE", "200000"))  # 200KB

# Reconnection
INITIAL_RECONNECT_DELAY = int(os.getenv("INITIAL_RECONNECT_DELAY", "1"))  # seconds
MAX_RECONNECT_DELAY = int(os.getenv("MAX_RECONNECT_DELAY", "30"))  # seconds

# Logging
LOG_INTERMEDIATE = os.getenv("LOG_INTERMEDIATE", "false").lower() == "true"

# ESP32 Default Cameras
DEFAULT_ESP32_CAMERAS = [
    {
        "device_id": "ESP32_CAM_01",
        "stream_url": "http://192.168.1.100:80/stream",
        "camera_name": "entrance",
        "location": "main_entrance",
    },
    {
        "device_id": "ESP32_CAM_02",
        "stream_url": "http://192.168.1.101:80/stream",
        "camera_name": "corridor",
        "location": "hallway",
    },
]


@lru_cache(maxsize=1)
def get_esp32_cameras() -> list:
    """Get ESP32 camera configuration from environment or defaults."""
    import json
    
    cameras_json = os.getenv("ESP32_CAMERAS_JSON")
    if cameras_json:
        try:
            return json.loads(cameras_json)
        except json.JSONDecodeError:
            pass
    
    return DEFAULT_ESP32_CAMERAS
```

### 3. `esp32_stream_adapter/requirements.txt`

```
numpy>=1.21.0
opencv-python>=4.5.0
requests>=2.28.0
requests[security]>=2.28.0
flask>=2.0.0
flask-cors>=3.0.0
python-dotenv>=0.20.0
pytest>=7.0.0
pytest-cov>=3.0.0
```

### 4. `surveillance_esp32_pipeline.py` (Simplified)

```python
"""Multi-camera ESP32 surveillance pipeline."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

import numpy as np

from esp32_stream_adapter.esp32_manager import ESP32CameraManager
from person_detection_module.detector import PersonDetector
from multi_object_tracking_module.tracker import MultiObjectTracker
from surveillance_backend_pipeline import SurveillanceBackendPipeline
from facial_recognition_module.src.face_node import FaceExtractorNode

logger = logging.getLogger(__name__)


class MultiCameraESP32Pipeline:
    """Orchestrates processing of multiple ESP32 camera feeds."""

    def __init__(
        self,
        esp32_config: dict,
        detection_model_path: str = None,
        tracking_backend: str = "deepsort",
        conf_threshold: float = 0.5,
    ):
        self.esp32_config = esp32_config
        self.camera_manager = ESP32CameraManager(esp32_config)
        
        # Per-camera components
        self.detectors: Dict[str, PersonDetector] = {}
        self.trackers: Dict[str, MultiObjectTracker] = {}
        self.face_node = FaceExtractorNode()
        self.backend_pipeline = SurveillanceBackendPipeline(face_node=self.face_node)
        
        self.frame_ids: Dict[str, int] = {}
        
        # Initialize
        if detection_model_path is None:
            from person_detection_module.config import MODEL_PATH
            detection_model_path = MODEL_PATH
        
        self._init_components(detection_model_path, tracking_backend, conf_threshold)

    def _init_components(self, model_path: str, backend: str, conf: float):
        """Initialize detection and tracking for each camera."""
        for cam_config in self.esp32_config.get("esp32_cameras", []):
            device_id = cam_config["device_id"]
            self.detectors[device_id] = PersonDetector(model_path=model_path, conf_threshold=conf)
            self.trackers[device_id] = MultiObjectTracker(backend=backend)
            self.frame_ids[device_id] = 0

    def start(self):
        """Start all camera streams."""
        self.camera_manager.start_all_streams()
        logger.info("ESP32 streams started")

    def process_next_frames(self) -> Dict[str, dict]:
        """Process latest frame from each camera."""
        results = {}
        all_frames = self.camera_manager.get_all_latest_frames()

        for device_id, (frame, timestamp) in all_frames.items():
            frame_id = self.frame_ids[device_id]
            self.frame_ids[device_id] += 1

            try:
                # Detection
                detection_output = self.detectors[device_id].detect(frame, frame_id)
                
                # Tracking
                tracking_output = self.trackers[device_id].update(detection_output, frame=frame)
                
                # Pipeline processing
                pipeline_result = self.backend_pipeline.process(
                    detection_output,
                    tracking_output,
                    frame,
                )

                results[device_id] = {
                    "status": "success",
                    "timestamp": timestamp.isoformat(),
                    "frame_id": frame_id,
                    "detections_count": len(detection_output.detections),
                    "tracks_count": len(tracking_output.tracks),
                    "alerts": pipeline_result.alerts,
                }

            except Exception as e:
                logger.error(f"[{device_id}] Error: {e}")
                results[device_id] = {"status": "error", "error": str(e)}

        return results

    def shutdown(self):
        """Shutdown pipeline."""
        self.camera_manager.stop_all_streams()
        logger.info("Pipeline shutdown")
```

### 5. `esp32_api_server.py` (Simplified)

```python
"""Flask API server for ESP32 multi-camera pipeline."""

from __future__ import annotations

import json
import logging
import os
from flask import Flask, Response, jsonify
import threading
import time

logger = logging.getLogger(__name__)

app = Flask(__name__)
pipeline = None
pipeline_lock = threading.Lock()


def init_pipeline(config: dict):
    """Initialize pipeline."""
    global pipeline
    from surveillance_esp32_pipeline import MultiCameraESP32Pipeline
    
    with pipeline_lock:
        pipeline = MultiCameraESP32Pipeline(
            esp32_config=config.get("esp32", {}),
            detection_model_path=config.get("detection", {}).get("model_path"),
            tracking_backend=config.get("tracking", {}).get("backend", "deepsort"),
            conf_threshold=config.get("detection", {}).get("conf_threshold", 0.5),
        )
        pipeline.start()
    
    logger.info("Pipeline initialized")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/status", methods=["GET"])
def status():
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503
    
    with pipeline_lock:
        camera_status = pipeline.camera_manager.get_status()
    
    return jsonify({
        "pipeline": "running",
        "cameras": camera_status,
    })


@app.route("/api/frames/process", methods=["POST"])
def process():
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503
    
    try:
        with pipeline_lock:
            results = pipeline.process_next_frames()
        return jsonify({
            "status": "success",
            "results": results,
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stream/all", methods=["GET"])
def stream_all():
    """SSE stream of all results."""
    def gen():
        while True:
            try:
                with pipeline_lock:
                    results = pipeline.process_next_frames()
                yield f"data: {json.dumps(results)}\n\n"
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Stream error: {e}")
                time.sleep(1)
    
    return Response(gen(), mimetype="text/event-stream")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    config_file = os.getenv("CONFIG_FILE", "esp32_config.json")
    with open(config_file) as f:
        config = json.load(f)
    
    init_pipeline(config)
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
```

### 6. `esp32_config.json` (Example)

```json
{
  "esp32": {
    "esp32_cameras": [
      {
        "device_id": "ESP32_CAM_01",
        "stream_url": "http://192.168.1.100:80/stream",
        "camera_name": "entrance",
        "location": "main_entrance",
        "resolution": "SVGA",
        "fps": 10
      },
      {
        "device_id": "ESP32_CAM_02",
        "stream_url": "http://192.168.1.101:80/stream",
        "camera_name": "corridor",
        "location": "hallway",
        "resolution": "SVGA",
        "fps": 10
      }
    ]
  },
  "detection": {
    "model_path": "person_detection_module/yolov8n.pt",
    "conf_threshold": 0.5
  },
  "tracking": {
    "backend": "deepsort"
  }
}
```

### 7. `Dockerfile.esp32`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 8080

CMD ["python", "esp32_api_server.py"]
```

### 8. ESP32 Firmware Template (Minimal)

```cpp
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// Configuration
const char* SSID = "YOUR_SSID";
const char* PASSWORD = "YOUR_PASSWORD";
const char* DEVICE_NAME = "ESP32_CAM_01";

// Pins (for AI Thinker ESP32-CAM)
#include "camera_pins.h"

WebServer server(80);

void setup() {
  Serial.begin(115200);
  initCamera();
  connectWiFi();
  setupServer();
}

void loop() {
  server.handleClient();
  delay(1);
}

void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXELFORMAT_JPEG;
  config.frame_size = FRAMESIZE_SVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  esp_camera_init(&config);
  Serial.println("Camera initialized");
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.print("\nIP: ");
  Serial.println(WiFi.localIP());
}

void setupServer() {
  server.on("/stream", HTTP_GET, []() {
    handleMjpegStream();
  });
  
  server.on("/health", HTTP_GET, []() {
    server.send(200, "application/json", "{\"status\": \"ok\"}");
  });
  
  server.begin();
  Serial.println("Server started");
}

void handleMjpegStream() {
  WiFiClient client = server.client();
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=123456789000000000000");
  client.println();
  
  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) break;
    
    client.print("--123456789000000000000\r\n");
    client.println("Content-Type: image/jpeg");
    client.println("Content-Length: " + String(fb->len));
    client.println("\r\n");
    client.write(fb->buf, fb->len);
    client.println();
    
    esp_camera_fb_return(fb);
    delay(100);  // ~10 FPS
  }
}
```

---

## Testing Commands

### Test ESP32 Stream

```bash
# Check if ESP32 is online
ping 192.168.1.100

# Test stream URL
curl -v http://192.168.1.100/stream

# Watch stream with VLC
vlc http://192.168.1.100/stream

# Save stream to file
ffmpeg -i http://192.168.1.100/stream -t 10 output.avi
```

### Test Cloud API

```bash
# Health check
curl http://localhost:8080/api/health

# Get status
curl http://localhost:8080/api/status | jq .

# Process frames
curl -X POST http://localhost:8080/api/frames/process | jq .

# Stream results (SSE)
curl http://localhost:8080/api/stream/all
```

---

## Docker Deployment

```bash
# Build image
docker build -f Dockerfile.esp32 -t esp32-surveillance .

# Run container
docker run -d \
  --name esp32-pipeline \
  -p 8080:8080 \
  -v $(pwd)/esp32_config.json:/app/esp32_config.json \
  -e CONFIG_FILE=esp32_config.json \
  esp32-surveillance

# View logs
docker logs -f esp32-pipeline

# Stop
docker stop esp32-pipeline
```

---

## Key Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Frames per ESP32** | 10 FPS | MJPEG encoding |
| **JPEG Size** | 15-50 KB | Depends on quality |
| **Bandwidth per Camera** | 1.5-5 Mbps | 10 FPS × 15-50 KB |
| **Total Bandwidth (2 cameras)** | 3-10 Mbps | Comfortable for WiFi |
| **Network Latency** | 50-200ms | WiFi dependent |
| **Cloud Processing Latency** | 100-400ms | Detection + tracking |
| **End-to-End Latency** | 200-600ms | Stream + processing |
| **Effective FPS** | 2-5 FPS | After processing |

---

## Troubleshooting Quick Guide

```
✓ ESP32 Boots
↓
✓ Camera Initializes (check serial)
↓
✓ WiFi Connects (check serial, IP printed)
↓
✓ Stream Available (test with curl)
↓
✓ Cloud Receives Frames (check /api/status)
↓
✓ Detection Works (check alert count)
↓
✓ Alerts Trigger (check output database)
```

**If stuck at any step:** Check the detailed troubleshooting section in the main plan.

---

## File Checklist

- [ ] `esp32_stream_adapter/__init__.py`
- [ ] `esp32_stream_adapter/config.py`
- [ ] `esp32_stream_adapter/mjpeg_receiver.py`
- [ ] `esp32_stream_adapter/esp32_manager.py`
- [ ] `esp32_stream_adapter/requirements.txt`
- [ ] `esp32_stream_adapter/tests/test_*.py`
- [ ] `surveillance_esp32_pipeline.py`
- [ ] `esp32_api_server.py`
- [ ] `esp32_config.json`
- [ ] `Dockerfile.esp32`
- [ ] `.env.esp32`
- [ ] ESP32 firmware (Arduino sketches)

---

## Integration Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Hardware** | 1-2 days | Assemble, test, flash firmware |
| **Cloud Module** | 2-3 days | Create adapter, stream receiver |
| **Pipeline** | 1-2 days | orchestrator, API server |
| **Testing** | 1-2 days | End-to-end, performance tuning |
| **Deployment** | 1 day | Docker, production setup |
| **Total** | **6-10 days** | **Full integration** |

