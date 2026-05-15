# ESP32 Integration: Complete Implementation Guide

## ⚠️ CRITICAL CLARIFICATION: Pipeline Runs on CLOUD ONLY

**The entire surveillance pipeline runs ONLY on the cloud server - NOT on the ESP32.**

The ESP32's role is **LIMITED to**:
- ✅ Capturing video frames from the camera
- ✅ Encoding frames to MJPEG format
- ✅ Streaming MJPEG video over HTTP via WiFi
- ❌ **NOT** running detection models
- ❌ **NOT** running tracking algorithms
- ❌ **NOT** running face recognition
- ❌ **NOT** storing data
- ❌ **NOT** making decisions

**ESP32 Limitations:**
- Limited RAM (160 KB) - cannot fit ML models
- Limited CPU (240 MHz) - cannot run inference
- Limited Storage (4 MB) - cannot store models
- Limited Power - streaming only, no intense processing

**Cloud Server Does ALL Processing:**
- Receives MJPEG stream from ESP32
- Decodes frames to raw images
- Runs YOLOv8 person detection
- Runs DeepSORT tracking
- Runs face recognition & clothing analysis
- Fuses all signals
- Makes alert decisions
- Stores results in Supabase

---

## 📋 Overview

You now have a complete plan to integrate 2 ESP32 cameras with your surveillance pipeline for real-time cloud processing. This document summarizes everything and provides step-by-step implementation instructions.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR NEW SYSTEM OVERVIEW                      │
└─────────────────────────────────────────────────────────────────┘

EDGE LAYER (On-Site)
├─ ESP32-CAM #1 (192.168.1.100)
│  ├─ OV2640 Camera Module
│  ├─ MJPEG Encoder (10 FPS)
│  └─ HTTP MJPEG Server (Port 80)
│
└─ ESP32-CAM #2 (192.168.1.101)
   ├─ OV2640 Camera Module
   ├─ MJPEG Encoder (10 FPS)
   └─ HTTP MJPEG Server (Port 80)


                    WiFi Network (2.4 GHz)
                  ↓ MJPEG over HTTP ↓


CLOUD LAYER (Your Server)
├─ ESP32StreamAdapter
│  ├─ MJPEGStreamReceiver (×2) - decodes streams
│  └─ ESP32CameraManager - orchestrates frame capture
│
├─ MultiCameraESP32Pipeline
│  ├─ PersonDetector (×2) - detects people
│  ├─ MultiObjectTracker (×2) - tracks people
│  ├─ FaceExtractor - identifies faces
│  ├─ FusionEngine - combines signals
│  └─ AlertDecision - makes decisions
│
├─ Flask API Server (Port 8080)
│  ├─ /api/health
│  ├─ /api/status
│  ├─ /api/frames/process
│  ├─ /api/stream/all (SSE)
│  └─ /api/camera/<id> (MJPEG)
│
└─ Output
   ├─ Supabase Database (alerts)
   └─ Dashboard/Notifications
```

---

## 📊 Document Guide

You have **2 comprehensive documents** for ESP32 integration:

### 1. **ESP32_INTEGRATION_PLAN.md** (Detailed Reference)
- 14 comprehensive parts
- Hardware pinouts and setup
- Complete firmware code (ready to upload)
- Cloud module architecture
- Database schema
- Troubleshooting guide
- Performance analysis
- **Read this for:** Understanding every detail, troubleshooting

### 2. **ESP32_INTEGRATION_QUICK_REFERENCE.md** (Quick Lookup)
- Architecture diagram
- File structure checklist
- Code templates (copy-paste ready)
- Testing commands
- Docker deployment
- Troubleshooting quick guide
- **Read this for:** Quick reference during development

---

## 🚀 STEP-BY-STEP IMPLEMENTATION

### PHASE 1: Hardware Setup (Day 1-2)

#### Step 1.1: Gather Hardware

```
For each ESP32-CAM:
├─ ESP32-CAM Board (with OV2640) × 2
├─ USB-TTL Serial Programmer × 1
├─ 5V Power Supply (500mA min) × 2
├─ Micro USB Cable × 2
├─ WiFi Network (2.4 GHz)
└─ Stability aids (tripod/mount)

Total cost: ~$40-60 per camera
```

#### Step 1.2: Hardware Assembly

**ESP32-CAM Connections:**
1. Insert OV2640 ribbon cable (connector should click)
2. Connect power: 5V to 5V pin, GND to GND
3. Set programming mode: Connect GPIO0 to GND
4. Connect Serial Programmer:
   ```
   USB-TTL → ESP32-CAM
   ├─ GND → GND
   ├─ TX → RX (GPIO 3)
   ├─ RX → TX (GPIO 1)
   └─ 5V → 5V
   ```

#### Step 1.3: Test Power

```
Expected:
├─ Red LED on ESP32 lights up
├─ Serial output on terminal
└─ No smoke/burning smell
```

### PHASE 2: Firmware Development (Day 2-3)

#### Step 2.1: Install Arduino IDE

```bash
# Download from: https://www.arduino.cc/en/software
# Or use PlatformIO (recommended)
```

#### Step 2.2: Configure Arduino IDE for ESP32

**Tools Menu:**
```
1. Board → Boards Manager
2. Search "ESP32"
3. Install "ESP32 by Espressif Systems" (latest version)
4. Board → Select "AI Thinker ESP32-CAM"
5. Port → Select COM port of USB-TTL
6. Upload Speed → 115200
7. Flash Mode → DIO
```

#### Step 2.3: Get the Firmware Code

**Option A: Use Template from Guide**
- Copy code from ESP32_INTEGRATION_PLAN.md (Part 2.1)
- Or from ESP32_INTEGRATION_QUICK_REFERENCE.md section 8

**Option B: More Features**
- See complete firmware in ESP32_INTEGRATION_PLAN.md

#### Step 2.4: Update Configuration in Code

```cpp
// ← IMPORTANT: Update these!
const char* SSID = "YOUR_SSID";           // Your WiFi name
const char* PASSWORD = "YOUR_PASSWORD";   // Your WiFi password
const char* DEVICE_NAME = "ESP32_CAM_01"; // Device 1 for first, Device 2 for second
```

#### Step 2.5: Compile & Upload

```
1. Click Verify (check mark) → Check for errors
2. Press RESET on ESP32
3. Click Upload (arrow) → Wait for "Leaving..."
4. Once done, open Serial Monitor (Tools → Serial Monitor)
5. Set baud rate to 115200
6. Press RESET button
7. Watch serial output
```

#### Step 2.6: Expected Serial Output

```
Starting ESP32-CAM MJPEG Server
Device: ESP32_CAM_01
Camera initialized successfully
WiFi connecting...
WiFi connected!
IP address: 192.168.1.100
HTTP server started
Stream available at: http://192.168.1.100/stream
```

#### Step 2.7: Test Stream in Browser/VLC

```bash
# Option 1: Browser
Open: http://192.168.1.100/stream
Should see moving MJPEG stream

# Option 2: VLC
Media → Open Network Stream
URL: http://192.168.1.100/stream

# Option 3: curl test
curl http://192.168.1.100/stream > output.mjpeg
```

#### Step 2.8: Repeat for Second ESP32

- Same firmware
- Change DEVICE_NAME to "ESP32_CAM_02"
- Expect different IP (probably 192.168.1.101)
- Test stream independently

### PHASE 3: Cloud Module Development (Day 3-5)

#### Step 3.1: Create Directory Structure

```bash
mkdir -p esp32_stream_adapter/tests
touch esp32_stream_adapter/__init__.py
touch esp32_stream_adapter/config.py
touch esp32_stream_adapter/mjpeg_receiver.py
touch esp32_stream_adapter/esp32_manager.py
touch esp32_stream_adapter/requirements.txt
touch esp32_stream_adapter/tests/__init__.py
touch esp32_stream_adapter/tests/test_mjpeg_receiver.py
```

#### Step 3.2: Copy Template Files

Use files from **ESP32_INTEGRATION_QUICK_REFERENCE.md**:

**File 1: `esp32_stream_adapter/__init__.py`**
```python
# Copy from section "1. `esp32_stream_adapter/__init__.py`"
```

**File 2: `esp32_stream_adapter/config.py`**
```python
# Copy from section "2. `esp32_stream_adapter/config.py`"
```

**File 3: `esp32_stream_adapter/requirements.txt`**
```
# Copy from section "3. `esp32_stream_adapter/requirements.txt`"
```

#### Step 3.3: Implement Core Classes

**Read the full implementations from ESP32_INTEGRATION_PLAN.md for:**
- `esp32_stream_adapter/mjpeg_receiver.py` (Part 3.2 - A)
- `esp32_stream_adapter/esp32_manager.py` (Part 3.2 - B)

```bash
# Copy class-by-class from PLAN document
# They have detailed docstrings and error handling
```

#### Step 3.4: Install Python Dependencies

```bash
pip install -r esp32_stream_adapter/requirements.txt
```

#### Step 3.5: Test Stream Receiver

```python
# test_receiver.py
from esp32_stream_adapter.mjpeg_receiver import MJPEGStreamReceiver

receiver = MJPEGStreamReceiver(
    device_id="ESP32_CAM_01",
    stream_url="http://192.168.1.100/stream"
)

connected = receiver.connect()
print(f"Connected: {connected}")

if connected:
    for i in range(10):
        frame = receiver.get_next_frame()
        if frame is not None:
            print(f"Frame {i} received: {frame[0].shape}")
        else:
            print(f"Frame {i} failed")
    
    receiver.disconnect()
```

**Run:**
```bash
python test_receiver.py
```

**Expected Output:**
```
[ESP32_CAM_01] Connecting to stream: http://192.168.1.100/stream
[ESP32_CAM_01] Connected successfully
Frame 0 received: (600, 800, 3)
Frame 1 received: (600, 800, 3)
...
[ESP32_CAM_01] Disconnected
```

### PHASE 4: Pipeline Integration (Day 5-6)

#### Step 4.1: Create Pipeline Orchestrator

**File: `surveillance_esp32_pipeline.py`**
- Copy template from ESP32_INTEGRATION_QUICK_REFERENCE.md (Section 4)
- Or detailed version from ESP32_INTEGRATION_PLAN.md (Part 3.2)

#### Step 4.2: Test Pipeline with Mock Data

```python
# test_pipeline.py
from surveillance_esp32_pipeline import MultiCameraESP32Pipeline

config = {
    "esp32_cameras": [
        {
            "device_id": "ESP32_CAM_01",
            "stream_url": "http://192.168.1.100/stream",
            "camera_name": "entrance",
        },
        {
            "device_id": "ESP32_CAM_02",
            "stream_url": "http://192.168.1.101/stream",
            "camera_name": "corridor",
        }
    ]
}

pipeline = MultiCameraESP32Pipeline(config)
pipeline.start()

# Let it run for a bit
import time
time.sleep(5)

# Process frames
results = pipeline.process_next_frames()
print("Results:", results)

pipeline.shutdown()
```

**Run:**
```bash
python test_pipeline.py
```

#### Step 4.3: Create Flask API Server

**File: `esp32_api_server.py`**
- Copy template from ESP32_INTEGRATION_QUICK_REFERENCE.md (Section 5)
- Or from ESP32_INTEGRATION_PLAN.md (Part 3.2)

#### Step 4.4: Create Configuration File

**File: `esp32_config.json`**
```json
{
  "esp32": {
    "esp32_cameras": [
      {
        "device_id": "ESP32_CAM_01",
        "stream_url": "http://192.168.1.100:80/stream",
        "camera_name": "entrance",
        "location": "main_entrance"
      },
      {
        "device_id": "ESP32_CAM_02",
        "stream_url": "http://192.168.1.101:80/stream",
        "camera_name": "corridor",
        "location": "hallway"
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

#### Step 4.5: Start Flask Server

```bash
python esp32_api_server.py
```

**Expected Output:**
```
* Running on http://0.0.0.0:8080
* WARNING: This is a development server...
```

### PHASE 5: Testing (Day 6-7)

#### Step 5.1: Test Health Endpoint

```bash
curl http://localhost:8080/api/health
# Expected: {"status": "healthy"}
```

#### Step 5.2: Test Status Endpoint

```bash
curl http://localhost:8080/api/status | jq .
# Expected: Connection status of both cameras
```

#### Step 5.3: Test Frame Processing

```bash
curl -X POST http://localhost:8080/api/frames/process | jq .
# Expected: Detection and tracking results
```

#### Step 5.4: Monitor Real-Time Stream

```bash
# Terminal 1: Run server
python esp32_api_server.py

# Terminal 2: Monitor stream
curl http://localhost:8080/api/stream/all
# Expected: Continuous SSE events with results
```

#### Step 5.5: Performance Benchmarking

```bash
# Measure processing latency
time curl -X POST http://localhost:8080/api/frames/process

# Should be <1 second per frame
```

### PHASE 6: Production Deployment (Day 7-8)

#### Step 6.1: Create Docker Image

**File: `Dockerfile.esp32`**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "esp32_api_server.py"]
```

#### Step 6.2: Build Docker Image

```bash
docker build -f Dockerfile.esp32 -t esp32-surveillance:latest .
```

#### Step 6.3: Run as Docker Container

```bash
docker run -d \
  --name esp32-pipeline \
  -p 8080:8080 \
  -v $(pwd)/esp32_config.json:/app/esp32_config.json \
  -e CONFIG_FILE=esp32_config.json \
  esp32-surveillance:latest

# View logs
docker logs -f esp32-pipeline

# Stop
docker stop esp32-pipeline
```

#### Step 6.4: Production Checklist

- [ ] Both ESP32 cameras stable (monitor for 24 hours)
- [ ] No WiFi disconnections
- [ ] No dropped frames
- [ ] Detection accuracy verified
- [ ] Alerts triggering correctly
- [ ] Database storing results
- [ ] Dashboard displaying live data
- [ ] Logs not showing errors
- [ ] Memory usage stable
- [ ] CPU usage <80%

---

## 📊 Quick Reference: ESP32 IP Addresses

Once both cameras are flashed and connected to WiFi:

| Device | IP Address | Stream URL | Expected |
|--------|-----------|-----------|----------|
| **ESP32_CAM_01** | 192.168.1.100* | http://192.168.1.100/stream | Entrance view |
| **ESP32_CAM_02** | 192.168.1.101* | http://192.168.1.101/stream | Corridor view |

*IP addresses may vary - check router's DHCP table or serial output

**Find IP Address:**
```bash
# Check your router's admin panel, or
arp -a  # On Windows
arp -a  # On Mac/Linux

# Look for entries like:
# 192.168.1.100    → ESP32 device
# 192.168.1.101    → ESP32 device
```

---

## 🧪 Testing Checklist

### Hardware Testing
- [ ] ESP32 boots (see serial output)
- [ ] Camera initializes (no errors)
- [ ] WiFi connects <10 seconds
- [ ] Stream plays without buffering
- [ ] No freezing/dropping frames

### Cloud Module Testing
- [ ] `mjpeg_receiver.py` connects to stream
- [ ] Receives 10+ consecutive frames
- [ ] Frame size correct (600×800×3)
- [ ] Timestamps accurate

### Pipeline Testing
- [ ] Detection runs on received frame
- [ ] Tracking maintains IDs across frames
- [ ] Face extraction works
- [ ] Fusion scores calculated
- [ ] Alerts triggered for detected people

### API Testing
- [ ] `/api/health` responds
- [ ] `/api/status` shows both cameras
- [ ] `/api/frames/process` returns results
- [ ] `/api/stream/all` streams continuously
- [ ] Response time <1s per frame

### Integration Testing
- [ ] Single camera: works perfectly
- [ ] Dual cameras: works simultaneously
- [ ] Database: alerts stored (Supabase)
- [ ] Dashboard: shows live results
- [ ] Error handling: handles disconnects gracefully

---

## 🔧 Common Issues & Solutions

### Issue: ESP32 Won't Connect to WiFi

**Symptoms:** Serial shows "Connecting..." repeatedly

**Solutions:**
1. Check SSID spelling (case-sensitive)
2. Make sure WiFi password is correct
3. Move ESP32 closer to WiFi router
4. Restart WiFi router
5. Check if WiFi is 2.4 GHz (not 5 GHz)

### Issue: Stream URL Unreachable

**Symptoms:** `curl http://192.168.1.100/stream` returns Connection refused

**Solutions:**
1. Verify ESP32 is online: `ping 192.168.1.100`
2. Check serial output for IP address
3. Try different port: `http://192.168.1.100:8080/stream`
4. Restart ESP32 (press RESET button)
5. Check firewall isn't blocking port 80

### Issue: Very Low FPS on Cloud

**Symptoms:** <5 FPS processing rate

**Solutions:**
1. Reduce JPEG quality on ESP32 (`jpeg_quality = 20`)
2. Reduce frame size on ESP32 (`FRAMESIZE_VGA`)
3. Increase cloud server CPU/GPU
4. Use lighter detection model (nano vs. small)
5. Process every 2nd frame: `if frame_count % 2 == 0: process()`

### Issue: Memory Leak or Slow Over Time

**Symptoms:** Pipeline slows down after hours

**Solutions:**
1. Check for unclosed file handles
2. Verify streams disconnecting properly
3. Monitor with `docker stats`
4. Restart container daily (cron job)
5. Profile with `memory_profiler`

---

## 📈 Expected Performance

Once deployed:

| Metric | Value | Notes |
|--------|-------|-------|
| **FPS per Camera** | 10 | MJPEG from ESP32 |
| **Effective Processing FPS** | 3-5 | After detection+tracking |
| **Latency** | 200-600ms | Edge to alert |
| **Bandwidth per Camera** | 2-5 Mbps | Depends on quality |
| **Total System Bandwidth** | 4-10 Mbps | Both cameras |
| **CPU Usage** | 30-60% | With 2 cameras |
| **Memory Usage** | 1-2 GB | Base + inference |
| **Accuracy** | 80-95% | Depends on setup |

---

## 📝 Files to Create Summary

```
New Files to Create:
├─ esp32_stream_adapter/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ mjpeg_receiver.py          [Part 3.2-A from PLAN]
│  ├─ esp32_manager.py           [Part 3.2-B from PLAN]
│  ├─ requirements.txt
│  └─ tests/
│     ├─ __init__.py
│     └─ test_mjpeg_receiver.py
│
├─ surveillance_esp32_pipeline.py [Part 3.2 or QUICK_REF]
├─ esp32_api_server.py            [Part 3.2 or QUICK_REF]
├─ esp32_config.json
├─ Dockerfile.esp32
└─ esp32_firmware.ino             [Part 2.1 from PLAN]

Total: ~15 files, ~3000-4000 lines of code
```

---

## 🎯 Success Criteria

Your integration is **COMPLETE** when:

✅ Both ESP32 cameras stream video reliably (24+ hours)
✅ Cloud receives all frames without gaps
✅ Person detection works on both cameras simultaneously
✅ Tracking IDs maintained across frames
✅ Alerts trigger for detected people
✅ Database stores all results
✅ Dashboard displays live data
✅ System recovers from WiFi disconnects
✅ Performance meets benchmarks
✅ No errors in logs

---

## 🚀 Quick Start Commands (All-in-One)

```bash
# 1. Create module structure
mkdir -p esp32_stream_adapter/tests

# 2. Copy template files (from QUICK_REF guide)
# - esp32_stream_adapter/__init__.py
# - esp32_stream_adapter/config.py
# - esp32_stream_adapter/mjpeg_receiver.py
# - esp32_stream_adapter/esp32_manager.py
# - esp32_stream_adapter/requirements.txt

# 3. Install dependencies
pip install -r esp32_stream_adapter/requirements.txt

# 4. Create pipeline files
# - surveillance_esp32_pipeline.py
# - esp32_api_server.py
# - esp32_config.json (update IPs)

# 5. Test locally
python esp32_api_server.py

# 6. Build Docker
docker build -f Dockerfile.esp32 -t esp32-surveillance .

# 7. Deploy
docker run -d --name esp32-pipeline -p 8080:8080 \
  -v $(pwd)/esp32_config.json:/app/esp32_config.json \
  esp32-surveillance

# 8. Monitor
docker logs -f esp32-pipeline
```

---

## 📞 Additional Resources

**From Your Project Guides:**
- Main details: ESP32_INTEGRATION_PLAN.md
- Quick lookup: ESP32_INTEGRATION_QUICK_REFERENCE.md
- Code templates: All sections have ready-to-copy code

**ESP32 Documentation:**
- Arduino IDE setup: https://docs.espressif.com/projects/arduino-esp32
- Camera driver: https://github.com/espressif/esp32-camera
- MJPEG streaming: Reference in firmware code

**Your Existing Pipeline:**
- Detection: `person_detection_module/`
- Tracking: `multi_object_tracking_module/`
- Fusion: `multi_attribute_fusion_module/`
- Alerts: `alert_decision_module/`

---

## 🎓 Learning Path

1. **Understand architecture** (30 min)
   - Read: ESP32_INTEGRATION_QUICK_REFERENCE.md - Architecture section

2. **Hardware assembly** (1-2 hours)
   - Follow: ESP32_INTEGRATION_PLAN.md - Part 6

3. **Firmware development** (2-3 hours)
   - Copy code from: ESP32_INTEGRATION_PLAN.md - Part 2
   - Test streaming

4. **Cloud module** (3-4 hours)
   - Implement: From PLAN and QUICK_REF templates
   - Test: With unit tests

5. **Pipeline integration** (2-3 hours)
   - Orchestrate components
   - Create API server

6. **Deploy & Optimize** (1-2 hours)
   - Docker setup
   - Performance tuning

**Total Time: 10-15 hours focused development**

---

You're all set! Start with **Phase 1: Hardware Setup** and work through each phase sequentially. Good luck! 🚀

