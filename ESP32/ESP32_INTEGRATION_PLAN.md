# ESP32 Camera Integration Plan
## Real-Time Cloud Processing Pipeline

---

## ⚠️ CRITICAL: Pipeline Runs on CLOUD ONLY - ESP32 is Streaming Device Only

**This is the most important architectural principle to understand before starting implementation:**

### What ESP32 DOES:
- ✅ Captures video from OV2640 camera
- ✅ Encodes frames as MJPEG
- ✅ Streams MJPEG over HTTP to cloud
- ✅ Maintains WiFi connection
- ✅ Runs autonomously without internet interruption

### What ESP32 DOES NOT:
- ❌ Run ML models (YOLOv8, InsightFace, etc.)
- ❌ Perform object detection or tracking
- ❌ Extract facial features
- ❌ Make alert decisions
- ❌ Access database
- ❌ Store processed data
- ❌ Run anything except MJPEG streaming firmware

### Why? Hardware Constraints:
- **RAM**: 160KB (insufficient for even smallest ML model >1MB)
- **CPU**: 240MHz dual-core (too slow for real-time inference)
- **Storage**: 4MB flash (no room for models + code + streaming)
- **WiFi**: 150 Mbps theoretical max (1-5 Mbps practical MJPEG streaming)

### Where Processing Happens:
**CLOUD SERVER** (your surveillance_backend_pipeline.py):
- PersonDetector → Person detection (YOLOv8)
- MultiObjectTracker → Track people (DeepSORT)
- FaceExtractor → Face recognition (InsightFace)
- ClothingFeatureExtractor → Clothing features
- FusionEngine → Combine all signals
- AlertDecision → Decide which alerts to send
- OutputDelivery → Save to Supabase + send alerts

---

## Executive Summary

This plan outlines how to integrate two ESP32 camera modules with your surveillance pipeline to stream footage in real-time to the cloud for processing. The architecture uses MJPEG-over-HTTP streaming from ESP32 devices, received and processed by your cloud-based surveillance backend.

**Key Points:**
- ESP32 cameras stream MJPEG video to cloud
- Cloud processes frames through your existing pipeline (detection → tracking → fusion → alerts)
- Support for real-time processing at 10-15 FPS per camera
- Dual-camera setup with synchronized processing

---

## Part 1: ESP32 Camera Module Overview

### 1.1 Hardware Setup

**Hardware Required:**
```
├── 2x ESP32 Development Board (e.g., ESP32-CAM or ESP32-WROOM)
├── 2x OV2640 Camera Module (or compatible sensor)
├── USB-TTL/Serial adapter for programming
├── Power supply (5V, 500mA minimum per device)
├── WiFi network (2.4 GHz recommended)
└── Network infrastructure (router, etc.)
```

**Hardware Specifications:**
| Component | Spec |
|-----------|------|
| **Processor** | ESP32 (240 MHz Dual-Core) |
| **RAM** | 160 KB (SRAM) |
| **Flash** | 4 MB |
| **WiFi** | 802.11 b/g/n |
| **Camera** | OV2640 (2MP, JPEG) |
| **Max FPS** | 30 FPS (depends on resolution) |
| **Typical FPS** | 10-15 FPS (for streaming) |
| **Video Output** | MJPEG over HTTP |

### 1.2 Camera Module Pinouts

**ESP32-CAM Common Pinout:**
```
OV2640 Camera → ESP32 Connections:
├── SIOD (SDA) → GPIO 21
├── SIOC (SCL) → GPIO 22
├── VSYNC → GPIO 25
├── HREF → GPIO 23
├── PCLK → GPIO 22
├── XCLK → GPIO 27
├── D7 → GPIO 19
├── D6 → GPIO 36
├── D5 → GPIO 18
├── D4 → GPIO 39
├── D3 → GPIO 5
├── D2 → GPIO 34
├── D1 → GPIO 35
└── D0 → GPIO 32

Power:
├── 5V → 5V pin
├── GND → GND pin
└── IO0 → GND (for programming)
```

### 1.3 ESP32 Memory Considerations

**Available Memory:**
```
Total: 160 KB SRAM
├── Used by WiFi Stack: ~40 KB
├── Used by Camera Driver: ~60 KB
├── Available for Buffering: ~50 KB (approx.)
└── Frame Buffer: ~50-100 KB (depends on resolution)

Implications:
• Limited frame buffering capability
• Streaming must be continuous (no long delays)
• MJPEG encoding helps reduce bandwidth
• Typical bandwidth: 50-200 KB/s (depends on quality)
```

---

## Part 2: ESP32 Firmware Code

### 2.1 Basic MJPEG Streaming Firmware

**File: `esp32_firmware_mjpeg_server.ino`**

```cpp
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ─────────────────────────────────────────────────────────────────────────────
//  Configuration
// ─────────────────────────────────────────────────────────────────────────────

// WiFi Configuration
const char* SSID = "YOUR_SSID";              // Change to your WiFi
const char* PASSWORD = "YOUR_PASSWORD";      // Change your password
const char* DEVICE_NAME = "ESP32_CAM_01";    // Unique device ID

// Cloud Configuration
const char* CLOUD_HOST = "your-cloud-ip.com";  // Your cloud server
const int CLOUD_PORT = 8080;                    // Your server port
const char* CLOUD_PATH = "/api/frames";        // Your endpoint

// Camera Configuration
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Server Configuration
WebServer server(80);
static const char* BOUNDARY = "123456789000000000000";
static const char* CONTENT_TYPE = "multipart/x-mixed-replace; boundary=123456789000000000000";

// ─────────────────────────────────────────────────────────────────────────────
//  Camera Initialization
// ─────────────────────────────────────────────────────────────────────────────

void initializeCamera() {
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

  // Camera settings
  config.xclk_freq_hz = 20000000;  // 20 MHz
  config.pixel_format = PIXELFORMAT_JPEG;
  config.frame_size = FRAMESIZE_SVGA;  // 800x600
  config.jpeg_quality = 12;  // 0-63, lower = better quality
  config.fb_count = 1;  // Frame buffer count

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }

  Serial.println("Camera initialized successfully");

  // Adjust camera settings
  sensor_t* s = esp_camera_sensor_get();
  s->set_brightness(s, 0);      // -2 to 2
  s->set_contrast(s, 0);        // -2 to 2
  s->set_saturation(s, 0);      // -2 to 2
  s->set_special_effect(s, 0);  // 0 to 6 (0 = none)
  s->set_whitebal(s, 1);        // Enable auto white balance
  s->set_awb_gain(s, 1);        // Auto white balance gain
  s->set_wb_mode(s, 0);         // 0 = Auto
  s->set_expose_ctrl(s, 1);     // Enable auto exposure
  s->set_aec_value(s, 300);     // 0-1200
  s->set_gain_ctrl(s, 1);       // Enable auto gain
  s->set_agc_gain(s, 0);        // 0-30
  s->set_gainceiling(s, (gainceiling_t)0);  // Image gain ceiling
  s->set_bpc(s, 0);             // BPC (Black Pixel Cancellation)
  s->set_wpc(s, 1);             // WPC (White Pixel Cancellation)
  s->set_raw_gma(s, 1);         // Enable raw gamma
  s->set_lenc(s, 1);            // Enable lens correction
  s->set_vflip(s, 0);           // Vertical flip
  s->set_hmirror(s, 0);         // Horizontal mirror
  s->set_dcw(s, 1);             // DCW (Downsize Mode)
  s->set_colorbar(s, 0);        // Enable color bar (0 = off)
}

// ─────────────────────────────────────────────────────────────────────────────
//  WiFi Setup
// ─────────────────────────────────────────────────────────────────────────────

void initializeWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  MJPEG Stream Handler
// ─────────────────────────────────────────────────────────────────────────────

void handleMjpegStream() {
  WiFiClient client = server.client();
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: " + String(CONTENT_TYPE));
  client.println("Access-Control-Allow-Origin: *");
  client.println();

  unsigned long lastFrameTime = 0;
  const unsigned long FRAME_INTERVAL = 100;  // ~10 FPS (100ms per frame)

  while (client.connected()) {
    unsigned long currentTime = millis();

    // Rate limiting: only capture frame every FRAME_INTERVAL ms
    if (currentTime - lastFrameTime >= FRAME_INTERVAL) {
      lastFrameTime = currentTime;

      camera_fb_t* fb = esp_camera_fb_get();
      if (!fb) {
        Serial.println("Frame buffer get failed");
        break;
      }

      // Send MJPEG boundary
      client.print("--");
      client.println(BOUNDARY);

      // Send HTTP headers for this frame
      client.println("Content-Type: image/jpeg");
      client.println("Content-Length: " + String(fb->len));
      client.println("X-Timestamp: " + String(millis()));
      client.println();

      // Send JPEG data
      client.write(fb->buf, fb->len);
      client.println();

      esp_camera_fb_return(fb);
    }

    // Small delay to prevent watchdog timeout
    delay(1);
  }

  Serial.println("Stream client disconnected");
}

// ─────────────────────────────────────────────────────────────────────────────
//  HTTP Server Setup
// ─────────────────────────────────────────────────────────────────────────────

void setupHTTPServer() {
  // MJPEG stream endpoint
  server.on("/stream", HTTP_GET, handleMjpegStream);

  // Health check endpoint
  server.on("/health", HTTP_GET, []() {
    server.send(200, "application/json", "{\"status\": \"ok\", \"device\": \"" + String(DEVICE_NAME) + "\"}");
  });

  // Camera settings JSON
  server.on("/config", HTTP_GET, []() {
    String json = "{\"device\": \"";
    json += DEVICE_NAME;
    json += "\", \"ssid\": \"";
    json += SSID;
    json += "\", \"ip\": \"";
    json += WiFi.localIP().toString();
    json += "\", \"fps\": 10}";
    server.send(200, "application/json", json);
  });

  server.begin();
  Serial.println("HTTP server started");
  Serial.println("Stream available at: http://" + WiFi.localIP().toString() + "/stream");
}

// ─────────────────────────────────────────────────────────────────────────────
//  Main Setup & Loop
// ─────────────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\nStarting ESP32-CAM MJPEG Server");
  Serial.println("Device: " + String(DEVICE_NAME));

  initializeCamera();
  initializeWiFi();
  setupHTTPServer();
}

void loop() {
  server.handleClient();
  delay(1);
}
```

### 2.2 Alternative: RTSP Stream Firmware

For more standard compatibility, you can use RTSP (Real Time Streaming Protocol):

**Key Advantages:**
- Standard protocol (ffmpeg, VLC compatible)
- Better error handling
- Audio support (if needed)
- Lower latency than MJPEG

**Library:** `esp32-rtsp` (available on GitHub)

```cpp
#include "RTSP.h"

RTSP rtsp;

void setup() {
  // ... camera init ...
  rtsp.begin("192.168.1.100", 554, "/stream");  // RTSP server
}

void loop() {
  rtsp.run();
}
```

---

## Part 3: Cloud Infrastructure Setup

### 3.1 New Module: `esp32_stream_adapter`

**Directory Structure:**
```
esp32_stream_adapter/
├── __init__.py
├── config.py
├── mjpeg_receiver.py
├── frame_processor.py
├── esp32_manager.py
├── requirements.txt
└── tests/
    ├── test_mjpeg_receiver.py
    └── test_frame_processor.py
```

### 3.2 Key Components

#### A. `mjpeg_receiver.py` - MJPEG Stream Decoder

```python
"""
MJPEG stream receiver - decodes MJPEG streams from ESP32 cameras.
"""

from __future__ import annotations

import logging
import io
import time
from typing import Optional, Tuple
from datetime import datetime

import cv2
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MJPEGStreamReceiver:
    """
    Receives and decodes MJPEG streams from ESP32 cameras.
    Handles network errors, reconnection, and frame extraction.
    """

    MJPEG_BOUNDARY = b"--123456789000000000000"
    STREAM_TIMEOUT = 10  # seconds

    def __init__(
        self,
        device_id: str,
        stream_url: str,
        max_reconnect_attempts: int = 5,
    ):
        """
        Initialize MJPEG stream receiver.

        Parameters
        ----------
        device_id : str
            Unique identifier for camera (e.g., "ESP32_CAM_01")
        stream_url : str
            Full URL to MJPEG stream (e.g., "http://192.168.1.10:80/stream")
        max_reconnect_attempts : int
            Maximum reconnection attempts before giving up
        """
        self.device_id = device_id
        self.stream_url = stream_url
        self.max_reconnect_attempts = max_reconnect_attempts

        self.session = self._create_robust_session()
        self.response: Optional[requests.Response] = None
        self.is_connected = False
        self.last_frame_time: Optional[datetime] = None
        self.frame_count = 0
        self.reconnect_count = 0

    def _create_robust_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def connect(self) -> bool:
        """
        Establish connection to MJPEG stream.

        Returns
        -------
        bool
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"[{self.device_id}] Connecting to stream: {self.stream_url}")
            self.response = self.session.get(
                self.stream_url,
                stream=True,
                timeout=self.STREAM_TIMEOUT,
            )
            self.response.raise_for_status()
            self.is_connected = True
            self.reconnect_count = 0
            logger.info(f"[{self.device_id}] Connected successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.device_id}] Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """Close stream connection."""
        if self.response:
            self.response.close()
        self.is_connected = False
        logger.info(f"[{self.device_id}] Disconnected")

    def get_next_frame(self) -> Optional[Tuple[np.ndarray, datetime]]:
        """
        Extract next JPEG frame from stream.

        Returns
        -------
        Optional[Tuple[np.ndarray, datetime]]
            (frame_array, timestamp) if successful, None if stream ends or error
        """
        if not self.is_connected or not self.response:
            return None

        try:
            # Find MJPEG boundary
            boundary_found = False
            frame_data = io.BytesIO()

            for chunk in self.response.iter_content(chunk_size=1024):
                if not chunk:
                    logger.warning(f"[{self.device_id}] Stream ended")
                    self.is_connected = False
                    return None

                frame_data.write(chunk)

                # Check if we have a complete JPEG frame
                if b"\xff\xd9" in frame_data.getvalue():  # JPEG end marker
                    # Extract JPEG data
                    jpeg_data = frame_data.getvalue()
                    start_idx = jpeg_data.find(b"\xff\xd8")  # JPEG start marker

                    if start_idx != -1:
                        jpeg_bytes = jpeg_data[start_idx : jpeg_data.rfind(b"\xff\xd9") + 2]

                        # Decode JPEG
                        frame = cv2.imdecode(
                            np.frombuffer(jpeg_bytes, dtype=np.uint8),
                            cv2.IMREAD_COLOR,
                        )

                        if frame is not None:
                            timestamp = datetime.now()
                            self.frame_count += 1
                            self.last_frame_time = timestamp
                            return (frame, timestamp)
                        else:
                            logger.warning(f"[{self.device_id}] Failed to decode JPEG")

                # Prevent buffer overflow
                if frame_data.tell() > 1000000:  # 1MB
                    frame_data.seek(0)
                    frame_data.truncate()

        except Exception as e:
            logger.error(f"[{self.device_id}] Error reading frame: {e}")
            self.is_connected = False
            return None

    def get_statistics(self) -> dict:
        """Return connection statistics."""
        return {
            "device_id": self.device_id,
            "is_connected": self.is_connected,
            "frames_received": self.frame_count,
            "last_frame_time": self.last_frame_time.isoformat() if self.last_frame_time else None,
            "reconnect_count": self.reconnect_count,
        }
```

#### B. `esp32_manager.py` - Multi-Camera Management

```python
"""
ESP32 camera manager - handles multiple ESP32 streams simultaneously.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np

from esp32_stream_adapter.mjpeg_receiver import MJPEGStreamReceiver

logger = logging.getLogger(__name__)


class ESP32CameraManager:
    """Manages multiple ESP32 camera streams."""

    def __init__(self, config: dict):
        """
        Initialize camera manager.

        Parameters
        ----------
        config : dict
            Configuration with esp32_cameras list:
            {
                "esp32_cameras": [
                    {
                        "device_id": "ESP32_CAM_01",
                        "stream_url": "http://192.168.1.10:80/stream",
                        "camera_name": "entrance"
                    },
                    ...
                ]
            }
        """
        self.config = config
        self.cameras: Dict[str, MJPEGStreamReceiver] = {}
        self.latest_frames: Dict[str, Tuple[np.ndarray, datetime]] = {}
        self.locks: Dict[str, threading.Lock] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}

        self._initialize_cameras()

    def _initialize_cameras(self) -> None:
        """Initialize all cameras from config."""
        esp32_cameras = self.config.get("esp32_cameras", [])

        for camera_config in esp32_cameras:
            device_id = camera_config["device_id"]
            stream_url = camera_config["stream_url"]

            receiver = MJPEGStreamReceiver(device_id, stream_url)
            self.cameras[device_id] = receiver
            self.locks[device_id] = threading.Lock()
            self.stop_events[device_id] = threading.Event()

            logger.info(f"Initialized camera: {device_id}")

    def start_all_streams(self) -> None:
        """Start all camera streams in background threads."""
        for device_id, receiver in self.cameras.items():
            self.threads[device_id] = threading.Thread(
                target=self._stream_worker,
                args=(device_id, receiver),
                daemon=True,
            )
            self.threads[device_id].start()

    def _stream_worker(self, device_id: str, receiver: MJPEGStreamReceiver) -> None:
        """
        Worker thread for each camera stream.
        Continuously reads frames and stores latest frame.
        """
        reconnect_delay = 1  # Initial delay, exponential backoff

        while not self.stop_events[device_id].is_set():
            try:
                # Connect
                if not receiver.connect():
                    logger.warning(
                        f"[{device_id}] Connection failed, retrying in {reconnect_delay}s"
                    )
                    self.stop_events[device_id].wait(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30)  # Cap at 30s
                    continue

                reconnect_delay = 1  # Reset delay on successful connection

                # Read frames continuously
                while not self.stop_events[device_id].is_set():
                    frame_data = receiver.get_next_frame()

                    if frame_data is None:
                        logger.warning(f"[{device_id}] Stream disconnected")
                        break

                    frame, timestamp = frame_data

                    with self.locks[device_id]:
                        self.latest_frames[device_id] = (frame, timestamp)

            except Exception as e:
                logger.error(f"[{device_id}] Stream worker error: {e}")
                receiver.disconnect()

    def get_latest_frame(self, device_id: str) -> Optional[Tuple[np.ndarray, datetime]]:
        """
        Get latest frame from specific camera.

        Parameters
        ----------
        device_id : str
            Camera device ID

        Returns
        -------
        Optional[Tuple[np.ndarray, datetime]]
            Latest (frame, timestamp) or None if no frame yet
        """
        if device_id not in self.cameras:
            logger.error(f"Unknown device: {device_id}")
            return None

        with self.locks[device_id]:
            return self.latest_frames.get(device_id)

    def get_all_latest_frames(self) -> Dict[str, Tuple[np.ndarray, datetime]]:
        """Get latest frame from all cameras."""
        frames = {}
        for device_id in self.cameras:
            frame_data = self.get_latest_frame(device_id)
            if frame_data is not None:
                frames[device_id] = frame_data
        return frames

    def stop_all_streams(self) -> None:
        """Stop all camera streams and cleanup."""
        for device_id in self.cameras:
            self.stop_events[device_id].set()

        # Wait for threads to finish
        for thread in self.threads.values():
            thread.join(timeout=5)

        # Disconnect all receivers
        for receiver in self.cameras.values():
            receiver.disconnect()

        logger.info("All streams stopped")

    def get_status(self) -> dict:
        """Get status of all cameras."""
        status = {}
        for device_id, receiver in self.cameras.items():
            status[device_id] = receiver.get_statistics()
        return status
```

---

## Part 4: Pipeline Integration

### 4.1 New Service: Multi-Camera ESP32 Pipeline

**File: `surveillance_esp32_pipeline.py`**

```python
"""
Multi-camera ESP32 surveillance pipeline orchestrator.
Processes frames from multiple ESP32 cameras through detection, tracking, and fusion.
"""

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
    """
    Orchestrates processing of multiple ESP32 camera feeds through
    the complete surveillance pipeline.
    """

    def __init__(
        self,
        esp32_config: dict,
        detection_model_path: str = None,
        tracking_backend: str = "deepsort",
        conf_threshold: float = 0.5,
    ):
        """
        Initialize multi-camera ESP32 pipeline.

        Parameters
        ----------
        esp32_config : dict
            Configuration with esp32_cameras list
        detection_model_path : str
            Path to detection model
        tracking_backend : str
            Tracking backend ("deepsort" or "bytetrack")
        conf_threshold : float
            Detection confidence threshold
        """
        self.esp32_config = esp32_config
        self.detection_model_path = detection_model_path
        self.tracking_backend = tracking_backend
        self.conf_threshold = conf_threshold

        # Initialize ESP32 manager
        self.camera_manager = ESP32CameraManager(esp32_config)

        # Initialize per-camera pipelines
        self.detectors: Dict[str, PersonDetector] = {}
        self.trackers: Dict[str, MultiObjectTracker] = {}
        self.face_node = FaceExtractorNode()
        self.backend_pipeline = SurveillanceBackendPipeline(face_node=self.face_node)

        # Frame IDs per camera
        self.frame_ids: Dict[str, int] = {}

        self._initialize_per_camera_components()

    def _initialize_per_camera_components(self) -> None:
        """Initialize detection and tracking for each camera."""
        if self.detection_model_path is None:
            from person_detection_module.config import MODEL_PATH
            self.detection_model_path = MODEL_PATH

        for camera_config in self.esp32_config.get("esp32_cameras", []):
            device_id = camera_config["device_id"]

            self.detectors[device_id] = PersonDetector(
                model_path=self.detection_model_path,
                conf_threshold=self.conf_threshold,
            )

            self.trackers[device_id] = MultiObjectTracker(
                backend=self.tracking_backend,
            )

            self.frame_ids[device_id] = 0

            logger.info(f"Initialized pipeline for {device_id}")

    def start(self) -> None:
        """Start all ESP32 camera streams."""
        self.camera_manager.start_all_streams()
        logger.info("ESP32 camera streams started")

    def process_next_frames(self) -> Dict[str, dict]:
        """
        Process latest frame from each camera.

        Returns
        -------
        Dict[str, dict]
            Results keyed by device_id
        """
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

                # Full pipeline processing (fusion, alerts, etc.)
                pipeline_result = self.backend_pipeline.process(
                    detection_output,
                    tracking_output,
                    frame,
                )

                results[device_id] = {
                    "status": "success",
                    "timestamp": timestamp.isoformat(),
                    "frame_id": frame_id,
                    "result": pipeline_result.to_dict(),
                }

            except Exception as e:
                logger.error(f"[{device_id}] Processing error: {e}")
                results[device_id] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": timestamp.isoformat(),
                }

        return results

    def get_status(self) -> dict:
        """Get status of all cameras and pipeline."""
        return {
            "cameras": self.camera_manager.get_status(),
            "pipeline": "running",
        }

    def shutdown(self) -> None:
        """Shutdown pipeline and camera streams."""
        self.camera_manager.stop_all_streams()
        logger.info("ESP32 pipeline shutdown complete")
```

### 4.2 Flask API Integration

**File: `esp32_api_server.py`**

```python
"""
Flask API server for ESP32 multi-camera pipeline.
Provides real-time frame processing and streaming endpoints.
"""

from __future__ import annotations

import json
import logging
from flask import Flask, Response, jsonify, send_from_directory
import threading
import time

from surveillance_esp32_pipeline import MultiCameraESP32Pipeline

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Global pipeline instance
pipeline: MultiCameraESP32Pipeline = None
pipeline_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
#  Initialization
# ─────────────────────────────────────────────────────────────────────────────

def initialize_pipeline(config: dict) -> None:
    """Initialize ESP32 pipeline with configuration."""
    global pipeline
    with pipeline_lock:
        pipeline = MultiCameraESP32Pipeline(
            esp32_config=config["esp32"],
            detection_model_path=config.get("detection_model_path"),
            tracking_backend=config.get("tracking_backend", "deepsort"),
            conf_threshold=config.get("conf_threshold", 0.5),
        )
        pipeline.start()
        logger.info("Pipeline initialized and started")


# ─────────────────────────────────────────────────────────────────────────────
#  API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "ESP32-Surveillance-Pipeline"})


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get pipeline and camera status."""
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503

    with pipeline_lock:
        status = pipeline.get_status()
    return jsonify(status)


@app.route("/api/frames/process", methods=["POST"])
def process_frames():
    """
    Process latest frames from all ESP32 cameras.
    Returns detection, tracking, and fusion results.
    """
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
        logger.error(f"Frame processing error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/camera/<device_id>", methods=["GET"])
def get_camera_frame(device_id):
    """
    Get latest frame from specific camera (as JPEG).
    Useful for monitoring/debugging.
    """
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503

    try:
        frame_data = pipeline.camera_manager.get_latest_frame(device_id)
        if frame_data is None:
            return jsonify({"error": f"No frame from {device_id}"}), 404

        frame, timestamp = frame_data

        import cv2
        success, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            return jsonify({"error": "JPEG encoding failed"}), 500

        return Response(
            jpeg.tobytes(),
            mimetype="image/jpeg",
            headers={"X-Timestamp": timestamp.isoformat()}
        )

    except Exception as e:
        logger.error(f"Error getting frame: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current configuration (non-sensitive fields only)."""
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503

    config = {
        "esp32_cameras": [
            {
                "device_id": cfg["device_id"],
                "camera_name": cfg.get("camera_name", "unknown"),
            }
            for cfg in pipeline.esp32_config.get("esp32_cameras", [])
        ],
        "tracking_backend": pipeline.tracking_backend,
        "conf_threshold": pipeline.conf_threshold,
    }
    return jsonify(config)


# ─────────────────────────────────────────────────────────────────────────────
#  Streaming Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/stream/all", methods=["GET"])
def stream_all_cameras():
    """
    Server-Sent Events (SSE) stream of all camera processing results.
    Yields JSON events with detection/tracking/alert results.
    """
    def event_generator():
        while True:
            try:
                with pipeline_lock:
                    results = pipeline.process_next_frames()

                # Send SSE event
                yield f"data: {json.dumps(results)}\n\n"
                time.sleep(0.1)  # 10 Hz processing rate

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/stream/<device_id>", methods=["GET"])
def stream_single_camera(device_id):
    """
    MJPEG stream of processed frames from single camera.
    Shows detection boxes, tracking IDs, etc.
    """
    if pipeline is None:
        return jsonify({"error": "Pipeline not initialized"}), 503

    def frame_generator():
        import cv2
        BOUNDARY = "123456789000000000000"

        while True:
            try:
                frame_data = pipeline.camera_manager.get_latest_frame(device_id)
                if frame_data is None:
                    continue

                frame, timestamp = frame_data

                # TODO: Draw overlay with detection/tracking boxes
                # overlay = _draw_pipeline_overlay(frame, results)

                success, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not success:
                    continue

                # MJPEG format
                yield (
                    b"--" + BOUNDARY.encode() + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg.tobytes())).encode() + b"\r\n"
                    + b"\r\n" + jpeg.tobytes() + b"\r\n"
                )

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Frame generation error: {e}")
                time.sleep(0.5)

    return Response(
        frame_generator(),
        mimetype="multipart/x-mixed-replace; boundary=" + "123456789000000000000"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Load configuration
    import os
    config_file = os.getenv("CONFIG_FILE", "esp32_config.json")

    try:
        with open(config_file) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found: {config_file}")
        exit(1)

    # Initialize pipeline
    initialize_pipeline(config)

    # Start Flask server
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("FLASK_PORT", 8080)),
        debug=debug,
        threaded=True,
    )
```

---

## Part 5: Configuration

### 5.1 ESP32 Configuration File

**File: `esp32_config.json`**

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
    "backend": "deepsort",
    "min_confidence": 0.3
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": false
  }
}
```

### 5.2 Environment Variables

**File: `.env.esp32`**

```bash
# ESP32 Configuration
ESP32_CONFIG_FILE=esp32_config.json

# Flask Server
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_DEBUG=false

# Detection
DETECTION_CONF_THRESHOLD=0.5
DETECTION_MODEL_PATH=person_detection_module/yolov8n.pt

# Tracking
TRACKING_BACKEND=deepsort

# Camera Stream
STREAM_TIMEOUT=10
MAX_RECONNECT_ATTEMPTS=5
STREAM_FRAME_RATE=10

# Logging
LOG_LEVEL=INFO
```

---

## Part 6: ESP32 Setup Instructions

### 6.1 Hardware Assembly

1. **Connect OV2640 to ESP32-CAM:**
   - Align camera connector carefully
   - Insert ribbon cable fully
   - Lock connector

2. **Connect Serial Programmer:**
   ```
   USB-TTL → ESP32-CAM
   ├── GND → GND
   ├── TX → RX
   ├── RX → TX
   └── 5V → 5V
   ```

3. **Set Programming Mode:**
   - GPIO0 → GND (for programming)
   - Press RESET button

### 6.2 Firmware Upload

1. **Install Arduino IDE** (or PlatformIO)

2. **Add ESP32 Board Manager:**
   - Boards → Boards Manager
   - Search "ESP32"
   - Install "ESP32 by Espressif Systems"

3. **Select Board:**
   - Tools → Board → "AI Thinker ESP32-CAM"
   - Tools → Port → (select serial port)
   - Tools → Upload Speed → 115200

4. **Compile and Upload:**
   - Paste code from Part 2.1
   - **Upload** button
   - Wait for "Writing at" messages

5. **Configure WiFi:**
   - Update SSID and PASSWORD in sketch
   - Re-upload to ESP32

### 6.3 Verify Connection

1. **Check Serial Monitor:**
   ```
   Starting ESP32-CAM MJPEG Server
   Camera init...
   WiFi connecting...
   WiFi connected!
   IP address: 192.168.1.100
   HTTP server started
   Stream available at: http://192.168.1.100/stream
   ```

2. **Test Stream (VLC or Browser):**
   ```bash
   vlc http://192.168.1.100/stream
   # Or open in browser: http://192.168.1.100/stream
   ```

---

## Part 7: Cloud Deployment

### 7.1 Requirements File

**File: `esp32_stream_adapter/requirements.txt`**

```
# Core dependencies
numpy>=1.21.0
opencv-python>=4.5.0

# HTTP/Streaming
requests>=2.28.0
flask>=2.0.0
flask-cors>=3.0.0

# Async processing (optional)
celery>=5.0.0
redis>=4.0.0

# Monitoring
prometheus-client>=0.14.0

# Testing
pytest>=7.0.0
pytest-cov>=3.0.0
```

### 7.2 Cloud Deployment (Docker)

**File: `Dockerfile.esp32`**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run Flask app
CMD ["python", "esp32_api_server.py"]
```

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  esp32-surveillance:
    build:
      context: .
      dockerfile: Dockerfile.esp32
    ports:
      - "8080:8080"
    environment:
      - FLASK_PORT=8080
      - CONFIG_FILE=esp32_config.json
      - FLASK_DEBUG=false
    volumes:
      - ./esp32_config.json:/app/esp32_config.json
      - ./runtime:/app/runtime
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

**Deploy:**
```bash
docker-compose -f docker-compose.yml up -d
```

---

## Part 8: Performance Considerations

### 8.1 Bandwidth Analysis

```
Per Camera:
├── Resolution: 800x600 JPEG
├── Quality: 12 (0-63 scale)
├── Frame Count: 10 FPS
├── Typical JPEG Size: 15-50 KB
└── Bandwidth: 150-500 KB/s = 1.2-4 Mbps

Two Cameras:
├── Total Bandwidth: 2.4-8 Mbps
├── WiFi 802.11n: 65-150 Mbps theoretical
└── Practical: Comfortable within typical WiFi bandwidth
```

### 8.2 Latency Analysis

```
End-to-End Latency (per frame):
├── Capture: ~100ms (10 FPS on ESP32)
├── JPEG Encoding: ~50ms
├── Network transmission: ~50ms (assuming good WiFi)
├── HTTP parsing: ~10ms
├── Detection: ~100ms
├── Tracking: ~20ms
├── Fusion & Decision: ~50ms
└── Total: ~380ms (~2.6 FPS effective)

Note: This is acceptable for surveillance applications
```

### 8.3 Optimization Tips

1. **Reduce Image Quality on ESP32 (if needed):**
   ```cpp
   config.jpeg_quality = 20;  // Lower = better compression
   config.frame_size = FRAMESIZE_VGA;  // 640x480 instead of 800x600
   ```

2. **Reduce FPS:**
   ```cpp
   FRAME_INTERVAL = 200;  // 5 FPS instead of 10
   ```

3. **Cloud-side Pooling:**
   ```python
   # Process every 2nd frame if behind on processing
   if frame_count % 2 == 0:
       process_frame()
   ```

4. **Use RTSP instead of MJPEG:**
   - More efficient
   - Better error handling
   - Lower latency

---

## Part 9: Testing & Debugging

### 9.1 ESP32 Debugging

**Serial Monitor Output Interpretation:**

```
Starting ESP32-CAM MJPEG Server
├── Device: ESP32_CAM_01 ✓
├── Camera init... ✓
├── WiFi connecting... ✓
├── Connected to: MY_SSID ✓
├── IP: 192.168.1.100 ✓
└── Stream available at: http://192.168.1.100/stream ✓

If any step fails, check:
• Camera connections (ribbon cable)
• WiFi credentials (SSID/password)
• Power supply (5V, 500mA)
• USB-TTL driver installed
```

### 9.2 Cloud-side Testing

```bash
# Test stream connection
curl -v http://192.168.1.100/stream

# Test processing endpoint
curl -X POST http://localhost:8080/api/frames/process

# Monitor status
curl http://localhost:8080/api/status | jq .

# Watch live stream (with ffmpeg)
ffmpeg -i http://192.168.1.100/stream -f sdl "ESP32 Stream"
```

### 9.3 Unit Tests

**File: `esp32_stream_adapter/tests/test_mjpeg_receiver.py`**

```python
import pytest
from esp32_stream_adapter.mjpeg_receiver import MJPEGStreamReceiver

def test_mjpeg_receiver_initialization():
    receiver = MJPEGStreamReceiver(
        device_id="TEST001",
        stream_url="http://localhost:8000/stream"
    )
    assert receiver.device_id == "TEST001"
    assert not receiver.is_connected

def test_mjpeg_boundary_detection():
    # Test MJPEG boundary marker recognition
    pass

def test_frame_extraction():
    # Test JPEG frame extraction from stream
    pass
```

---

## Part 10: Monitoring & Logging

### 10.1 Health Checks

```python
# Endpoint: /api/status
{
  "cameras": {
    "ESP32_CAM_01": {
      "device_id": "ESP32_CAM_01",
      "is_connected": true,
      "frames_received": 1523,
      "last_frame_time": "2024-04-08T10:15:32.123Z",
      "reconnect_count": 0
    },
    "ESP32_CAM_02": {
      "device_id": "ESP32_CAM_02",
      "is_connected": true,
      "frames_received": 1521,
      "last_frame_time": "2024-04-08T10:15:32.456Z",
      "reconnect_count": 0
    }
  },
  "pipeline": "running"
}
```

### 10.2 Key Metrics to Monitor

```python
# Per Camera
├── Frame Rate (FPS)
├── Network Latency (ms)
├── Connection Status (connected/disconnected)
├── Reconnection Count
└── Data Rate (MB/s)

# Per Processing Pipeline
├── Detection FPS
├── Tracking IDs (active)
├── Alert Rate (per minute)
├── Processing Latency (ms)
└── Error Rate (%)

# System
├── CPU Usage
├── Memory Usage
├── Disk I/O
└── Network Bandwidth
```

---

## Part 11: Troubleshooting Guide

| Issue | Symptoms | Cause | Solution |
|-------|----------|-------|----------|
| **ESP32 Not Connecting to WiFi** | Serial shows "Connecting..." repeatedly | Wrong SSID/password, weak signal | Verify credentials, move closer to router |
| **Stream URL 404** | curl returns 404 | Wrong IP or port | Check with `arp -a`, verify flask port in code |
| **Very Slow Stream** | <1 FPS, high latency | Network congestion, high JPEG quality | Reduce quality, check WiFi signal strength |
| **Frames Dropping** | Detection/tracking inconsistent | Processing slower than capture rate | Reduce FPS on ESP32, increase cloud CPU |
| **Camera Image Upside Down** | Video appears inverted | Normal behavior (camera mounted) | enable vflip in config: `s->set_vflip(s, 1)` |
| **Blurry Frames** | Low-power light exposure issue | Camera focus or lighting | Use external light, adjust exposure settings |
| **Frequent Reconnects** | Stream cuts out every 10-30s | Unstable WiFi, power issues | Use stable power supply, move away from interference |
| **High CPU on Cloud** | Processing lag, alerts delayed | Detection model too large, high FPS | Reduce resolution, use lighter model |

---

## Part 12: Integration Checklist

### Phase 1: Hardware Setup (Day 1)
- [ ] Assemble ESP32-CAM × 2
- [ ] Connect USB-TTL programmer
- [ ] Test power supply
- [ ] Verify camera ribbon cable connection

### Phase 2: ESP32 Firmware (Day 2)
- [ ] Install Arduino IDE
- [ ] Add ESP32 board manager
- [ ] Configure WiFi credentials in code
- [ ] Upload firmware to both boards
- [ ] Verify stream at http://device-ip/stream
- [ ] Test health endpoint: http://device-ip/health

### Phase 3: Cloud Module Creation (Day 3-4)
- [ ] Create `esp32_stream_adapter/` module
- [ ] Implement `mjpeg_receiver.py`
- [ ] Implement `esp32_manager.py`
- [ ] Write unit tests

### Phase 4: Pipeline Integration (Day 4-5)
- [ ] Create `surveillance_esp32_pipeline.py`
- [ ] Update `surveillance_backend_pipeline.py` (if needed)
- [ ] Implement Flask API: `esp32_api_server.py`
- [ ] Create `esp32_config.json`

### Phase 5: Testing & Deployment (Day 5-6)
- [ ] Test single camera first
- [ ] Test dual camera processing
- [ ] Performance benchmarking
- [ ] Deploy to cloud (Docker)
- [ ] Monitor logs and metrics

### Phase 6: Optimization (Ongoing)
- [ ] Fine-tune JPEG quality / FPS
- [ ] Monitor bandwidth usage
- [ ] Optimize processing pipeline
- [ ] Add redundancy/failover

---

## Part 13: Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────┘

LOCAL NETWORK (WiFi 2.4 GHz)
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ESP32-CAM #1 (192.168.1.100)                              │
│  ├─ OV2640 Camera                                          │
│  ├─ MJPEG Encoder                                          │
│  └─ HTTP Server (Port 80)                                  │
│       ↓ WiFi ↓ (MJPEG Stream)                              │
│                                                              │
│  ESP32-CAM #2 (192.168.1.101)                              │
│  ├─ OV2640 Camera                                          │
│  ├─ MJPEG Encoder                                          │
│  └─ HTTP Server (Port 80)                                  │
│       ↓ WiFi ↓ (MJPEG Stream)                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
         ↓ WiFi ↓

CLOUD SERVER
┌──────────────────────────────────────────────────────────────┐
│  ESP32 Stream Adapter Module                                │
│  ├─ MJPEGStreamReceiver (×2)                               │
│  │  ├─ HTTP client                                         │
│  │  ├─ frame decoder                                       │
│  │  └─ reconnection logic                                  │
│  │                                                           │
│  └─ ESP32CameraManager                                     │
│     ├─ Thread per camera                                   │
│     ├─ Latest frame buffer                                 │
│     └─ Status tracking                                     │
│           ↓                                                  │
│  Surveillance Pipeline (Existing)                          │
│  ├─ PersonDetector                                         │
│  ├─ MultiObjectTracker                                    │
│  ├─ FaceFeatureExtractor                                  │
│  ├─ ClothingFeatureExtractor                              │
│  ├─ FusionEngine                                          │
│  ├─ AlertDecision                                         │
│  └─ OutputDelivery → Supabase [DB]                        │
│           ↓                                                  │
│  Flask API Server (Port 8080)                             │
│  ├─ /api/status                                            │
│  ├─ /api/frames/process                                    │
│  ├─ /api/camera/<id>                                       │
│  ├─ /api/stream/all (SSE)                                  │
│  └─ /api/stream/<id> (MJPEG)                               │
│           ↓                                                  │
└──────────────────────────────────────────────────────────────┘
         ↓ HTTP/JSON ↓

CLIENT APPLICATIONS
├─ Web Dashboard
├─ Mobile App
└─ Alert System
```

---

## Part 14: Next Steps

1. **Prepare ESP32 Hardware** (1-2 days)
   - Assemble devices
   - Test power & connections
   - Prepare WiFi network

2. **Flash Firmware** (1 day)
   - Program both boards
   - Verify streams
   - Document IP addresses

3. **Build Cloud Module** (3-4 days)
   - Create adapter code
   - Unit tests
   - Integration testing

4. **Integrate with Pipeline** (1-2 days)
   - Connect to existing modules
   - Test end-to-end processing

5. **Deploy & Monitor** (1 day)
   - Docker deployment
   - Health monitoring
   - Performance tuning

**Total Timeline: 1-2 weeks for full integration**

---

