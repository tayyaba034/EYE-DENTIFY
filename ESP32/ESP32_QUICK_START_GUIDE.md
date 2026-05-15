# ESP32 Dual-Camera Setup: Quick Start Guide

**Project:** Surveillance Pipeline - 2 Camera System  
**Date:** April 17, 2026  
**Time to Implementation:** 2-3 weeks  

---

## TL;DR - Exact Hardware You Need

### Minimum Setup (~$56)
```
✓ 2× ESP32-CAM (AI Thinker) ............................ $36 ($18 each)
✓ 2× USB Power 5V 2A .................................... $16 ($8 each)
✓ 1× USB-TTL Programmer (CH340G) ....................... $4
✓ (Already have: WiFi router, jumper wires, cables)

Total: $56 + WiFi router (likely already have)
```

### Production Setup (~$300)
```
✓ 2× ESP32-S3-DevKitC-1-N16R8V .......................... $56 ($28 each)
✓ 2× OV2640 Camera Module (High Quality) ............... $44 ($22 each)
✓ 1× FTDI FT232RL USB Programmer ........................ $12
✓ 1× Industrial 5V 20A Power Supply (Mean Well) ........ $42
✓ 2× Shielded Cat6 Cables ............................... $30 ($15 each)
✓ 2× NEMA 4X Weatherproof Enclosures ................... $110 ($55 each)
✓ Misc (cable glands, brackets, wiring) ............... $4

Total: ~$298
```

---

## CRITICAL: What Processing Happens WHERE?

### ❌ DO NOT TRY TO RUN ML MODELS ON ESP32

| Processing Task | Location | Reason |
|-----------------|----------|--------|
| Capture frames from camera | **ESP32** | Built-in OV2640 interface |
| Encode to MJPEG | **ESP32** | On-chip encoder |
| Stream MJPEG over WiFi | **ESP32** | Simple HTTP server |
| **Person detection (YOLOv8)** | **CLOUD** | Requires 500MB+ model, GPU |
| **Face recognition** | **CLOUD** | Requires deep learning, GPU |
| **Facial detection** | **CLOUD** | Cannot run on 160KB RAM |
| Clothing color analysis | **CLOUD** | Requires image processing |
| Alert decisions | **CLOUD** | Complex logic with history |
| Database storage | **CLOUD** | Persistent data |

**Your Role as Developer:**
1. Upload simple MJPEG firmware to 2× ESP32 boards
2. Write Python code to receive MJPEG streams on cloud
3. Process streams through existing surveillance_backend_pipeline.py
4. Display results on dashboard

---

## STEP-BY-STEP SETUP (2-3 Weeks)

### Week 1: Hardware Assembly

**Day 1 - Procurement**
```bash
□ Order 2× ESP32-CAM + OV2640 (or buy from local store)
□ Order USB-TTL programmer
□ Order 2× USB power adapters
□ Verify WiFi router available (2.4 GHz band)
```

**Day 2-3 - Assembly**
```
For Each ESP32-CAM:
├─ Remove ribbon cable from packaging
├─ Align ribbon with camera slot (blue side facing microcontroller)
├─ Insert ribbon into slot until it clicks (don't force)
├─ Connect 5V power → 5V pin
├─ Connect GND power → GND pin
└─ Verify no bent pins

For USB-TTL Programmer:
├─ Identify TX/RX pins
├─ Cross-connect to ESP32:
│  ├─ Programmer TX → ESP32 RXD (GPIO 3)
│  ├─ Programmer RX → ESP32 TXD (GPIO 1)
│  ├─ Programmer GND → ESP32 GND
│  └─ Programmer 5V → ESP32 5V (only for flashing)
└─ Secure with tape/breadboard
```

**Day 4 - Test Power**
```
□ Connect 5V USB power to **first** ESP32-CAM
□ Observe: Red LED lights up (power good)
□ Observe: No burning smell, no smoke
□ Disconnect
□ Repeat for second ESP32-CAM
```

---

### Week 2: Firmware Upload

**Day 1 - Install Arduino IDE**
```bash
# Download from https://www.arduino.cc/en/software
# Or use PlatformIO (recommended for advanced users)

# Extract and run Arduino IDE
# Tools → Board Manager → Search "esp32" → Install latest
```

**Day 2 - Configure Arduino IDE**
```
Tools → Board → Select: AI Thinker ESP32-CAM
Tools → Upload Speed → 115200
Tools → Flash Mode → DIO
Tools → Port → COM3 (or your USB serial port)
```

**Day 3 - Get Firmware Code**

**Option A: Basic Firmware (Simplest)**
```cpp
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

const char* SSID = "YOUR_SSID";           // ← UPDATE
const char* PASSWORD = "YOUR_PASSWORD";   // ← UPDATE
const char* DEVICE_ID = "ESP32_CAM_01";   // ← Device 1 for first, Device 2 for second

// [Rest of firmware code from ESP32_INTEGRATION_PLAN.md Part 2.1]
```

**Get Full Code From:**
- `d:\FYP MODELS\PIPELINE\ESP32\ESP32_INTEGRATION_PLAN.md` (Part 2.1)
- Copy entire firmware module
- Paste into Arduino IDE

**Day 4 - Compile & Upload (FIRST ESP32)**
```
1. Update SSID and PASSWORD in code
2. Update DEVICE_ID = "ESP32_CAM_01"
3. Connect USB-TTL programmer to first ESP32
4. Set GPIO0 to GND (for programming mode)
5. Click Verify (checkmark) → Check for compile errors
6. Click Upload (arrow) → Watch for "Writing at..." messages
7. Should see: "Leaving... Magic trail bytes: 07 17 b8 ea"
8. Disconnect USB-TTL after upload completes
```

**Day 5 - Upload (SECOND ESP32)**
```
1. Copy and paste firmware code again
2. Update DEVICE_ID = "ESP32_CAM_02"       ← ONLY change this
3. Connect USB-TTL to second ESP32
4. Repeat upload process
5. Verify completion
```

**Day 6 - Test MJPEG Streams**
```bash
# Connect first ESP32 to power (no USB-TTL needed now)
# Wait 10 seconds for WiFi connection
# Open browser: http://192.168.1.100:80/stream
# Should see: MJPEG video stream in browser

# Connect second ESP32 to power
# Wait 10 seconds
# Open browser: http://192.168.1.101:80/stream
# Should see: MJPEG video stream

# If no video:
#   - Check WiFi SSID/password in serial monitor (115200 baud)
#   - Check IP address shown in serial output
#   - Verify camera ribbon inserted correctly
```

---

### Week 2-3: Cloud Setup

**Day 1-2 - Install Python Dependencies**
```bash
# On your cloud server

cd d:\FYP\ MODELS\PIPELINE

# Create virtual environment (if not existing)
python -m venv venv
venv\Scripts\activate

# Install streaming dependencies
pip install requests opencv-python numpy

# Verify existing dependencies are installed:
pip install -r requirements.txt  # If exists
```

**Day 3 - Create ESP32 Integration Module**
```bash
# Copy these files from documentation to your project:
mkdir esp32_stream_adapter
# Create: __init__.py
# Create: config.py
# Create: mjpeg_receiver.py
# Create: esp32_manager.py

# See ESP32_CLOUD_INTEGRATION_ARCHITECTURE.md for complete code
```

**Day 4 - Create Integration Pipeline**
```bash
# Copy surveillance_esp32_pipeline.py from documentation
# Update camera_configs with your IP addresses:

camera_configs = [
    {
        "device_id": "ESP32_CAM_01",
        "stream_url": "http://192.168.1.100:80/stream",  # Update IP if different
        "camera_name": "entrance",
        "location": "main_entrance",
    },
    {
        "device_id": "ESP32_CAM_02",
        "stream_url": "http://192.168.1.101:80/stream",  # Update IP if different
        "camera_name": "corridor",
        "location": "hallway",
    },
]
```

**Day 5-6 - Test Integration**
```bash
# Run test script
python -c "
from esp32_stream_adapter import ESP32CameraManager

configs = [
    {'device_id': 'ESP32_CAM_01', 'stream_url': 'http://192.168.1.100:80/stream', 'camera_name': 'entrance', 'location': 'main'},
    {'device_id': 'ESP32_CAM_02', 'stream_url': 'http://192.168.1.101:80/stream', 'camera_name': 'corridor', 'location': 'hall'},
]

manager = ESP32CameraManager(configs)
manager.start()

import time
time.sleep(3)  # Wait for streams to connect
stats = manager.get_stats()
print(stats)
"

# Expected output:
# {
#   'ESP32_CAM_01': {'frames_decoded': 5, 'reconnect_attempts': 0, ...},
#   'ESP32_CAM_02': {'frames_decoded': 5, 'reconnect_attempts': 0, ...}
# }
```

---

## PINOUT REFERENCES

### ESP32-CAM to OV2640 Connections (Already Done - Onboard)
```
These connections are factory-soldered. DO NOT MODIFY.

GPIO 21 (SIOD/SDA) ← I2C data
GPIO 22 (SIOC/SCL) ← I2C clock
GPIO 25 (VSYNC)    ← Frame sync
GPIO 23 (HREF)     ← Line sync
GPIO 22 (PCLK)     ← Pixel clock
GPIO 27 (XCLK)     ← Camera crystal clock
GPIO 19 (D7)       ← Data bit 7
... (D6-D0 on GPIO 36, 18, 39, 5, 34, 35, 32)
```

### Your Custom Connections (For Programming)
```
USB-TTL Programmer ←→ ESP32-CAM

GND ——————— GND (ground level matching)
TX ———————— RX (GPIO 3)
RX ———————— TX (GPIO 1)
5V ———————— 5V (only during programming)
DTR ———————— GPIO 0 (auto-reset - optional)
```

### Power Delivery
```
USB Power Adapter (5V 2A)
├─ Red wire → 5V pin on ESP32-CAM
├─ Black wire → GND pin on ESP32-CAM
└─ Secure with tape or wire crimp
```

---

## NETWORK CONFIGURATION

### WiFi Setup in Firmware

**Update these values in firmware:**
```cpp
const char* SSID = "YOUR_SSID";              // Your WiFi network name
const char* PASSWORD = "YOUR_PASSWORD";       // Your WiFi password
const char* DEVICE_ID = "ESP32_CAM_01";      // Unique per device
```

### Static IP Assignment (Optional but Recommended)

**In firmware (before WiFi.begin):**
```cpp
IPAddress STATIC_IP(192, 168, 1, 100);       // Device 1
IPAddress GATEWAY(192, 168, 1, 1);           // Your router
IPAddress SUBNET(255, 255, 255, 0);          
IPAddress DNS(8, 8, 8, 8);

WiFi.config(STATIC_IP, GATEWAY, SUBNET, DNS);
WiFi.begin(SSID, PASSWORD);
```

**For Device 2:**
```cpp
IPAddress STATIC_IP(192, 168, 1, 101);       // Change ONLY this line
// Rest remains same
```

---

## TROUBLESHOOTING

### "No video in browser at http://192.168.1.100:80/stream"

**Check 1: Is ESP32 connected to WiFi?**
```bash
# Connect USB-TTL and open Serial Monitor (Tools → Serial Monitor)
# Baud rate: 115200
# Should see:
#   Connecting to WiFi...
#   WiFi connected
#   IP address: 192.168.1.100
#   Streaming on: http://192.168.1.100:80/stream
```

**Check 2: Can you ping the ESP32?**
```bash
ping 192.168.1.100
# Should see replies (e.g., "Reply from 192.168.1.100: bytes=32 time=15ms")
```

**Check 3: Is camera ribbon inserted correctly?**
```
- Ribbon should slide into slot until it clicks
- Blue side should face the microcontroller
- Don't force it (will damage)
- Try removing and reinserting
```

**Check 4: Is power correct?**
```bash
# Measure voltage with multimeter:
# Between 5V and GND should read 4.8-5.2V
# Between 3.3V and GND should read 3.0-3.6V
# If not, check power supply and connections
```

### "Connection refused when accessing http://192.168.1.100:80/stream"

**Likely causes:**
1. ESP32 IP address is different than expected
   - Check serial monitor output for actual IP
   - Update browser URL accordingly

2. WiFi password incorrect
   - Check SSID/PASSWORD in code
   - Re-upload firmware with correct credentials

3. Firewall blocking
   - Check Windows Firewall settings
   - Allow port 80 through firewall

### "Frames not decoding in Python"

**Check:**
```python
# Check if frames are actually being received
from esp32_stream_adapter import MJPEGStreamReceiver

receiver = MJPEGStreamReceiver(
    stream_url="http://192.168.1.100:80/stream",
    camera_id="ESP32_CAM_01",
)

# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

receiver.start()
import time
time.sleep(5)

stats = receiver.get_stats()
print(f"Decoded frames: {stats['frames_decoded']}")
# Should be > 0

if stats['frames_decoded'] == 0:
    print(f"Error: {stats['last_error']}")
```

---

## PERFORMANCE MONITORING

### Check FPS Per Camera
```python
from esp32_stream_adapter import ESP32CameraManager
import time

manager = ESP32CameraManager([...configs...])
manager.start()

time.sleep(10)

stats = manager.get_stats()
for camera_id, camera_stats in stats.items():
    frames = camera_stats['frames_decoded']
    fps = frames / 10  # 10 seconds elapsed
    print(f"{camera_id}: {fps:.1f} FPS")
```

**Expected:** 8-12 FPS per camera (depends on WiFi quality)

### Check Network Bandwidth
```bash
# Use WiFi analyzer tool to check signal strength
# Open router admin page (usually 192.168.1.1)
# Look for connected devices - should see 2 ESP32-CAM
# Check signal strength (should be -50 to -70 dBm)

# If < -80 dBm: Move ESP32 closer to router
```

### Check CPU Usage on Cloud Server
```bash
# Windows Task Manager
# Process: python.exe
# CPU: Should be 10-30% for 2 cameras
# Memory: Should be 1-2 GB

# If higher: Check for memory leaks in frame buffer
```

---

## PRODUCTION DEPLOYMENT

### Step 1: Static IP Assignment (Router Level)
```
1. Login to router admin (192.168.1.1)
2. DHCP → Reserved/Static IP section
3. Find ESP32_CAM_01 MAC address
4. Assign: 192.168.1.100
5. Find ESP32_CAM_02 MAC address
6. Assign: 192.168.1.101
```

### Step 2: Mount Cameras
```
1. Choose locations with good WiFi signal
2. Mount bracket on wall/ceiling
3. Attach ESP32-CAM to bracket
4. Route USB power cable to nearest outlet
5. Connect USB power adapter
6. Verify stream loads in browser
```

### Step 3: Enable Cloud Service Autostart
```bash
# Windows:
# Create batch file: start_surveillance.bat
@echo off
cd d:\FYP MODELS\PIPELINE
call venv\Scripts\activate
python surveillance_esp32_pipeline.py

# Add to Windows Task Scheduler
# Run at startup, run with highest privileges
```

### Step 4: Monitor System Health
```python
# Create health check script
import requests
import time

while True:
    try:
        # Check camera 1
        r1 = requests.get("http://192.168.1.100:80/stream", timeout=5)
        status1 = "OK" if r1.status_code == 200 else "FAIL"
        
        # Check camera 2
        r2 = requests.get("http://192.168.1.101:80/stream", timeout=5)
        status2 = "OK" if r2.status_code == 200 else "FAIL"
        
        print(f"[{time.strftime('%H:%M:%S')}] Camera 1: {status1}, Camera 2: {status2}")
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
    
    time.sleep(60)  # Check every minute
```

---

## COST & TIME SUMMARY

| Phase | Time | Cost | Deliverable |
|-------|------|------|-------------|
| Procurement | 1-3 days | $56-300 | 2 ESP32 units + power |
| Assembly | 1-2 days | -  | Hardware ready |
| Firmware | 1-2 days | - | Firmware uploaded |
| Testing | 1 day | - | MJPEG streams verified |
| Cloud Integration | 2-3 days | - | Python code ready |
| Deployment | 1 day | - | Cameras mounted + live |
| **TOTAL** | **2-3 weeks** | **$56-300** | **Full system** |

---

## NEXT: Full Documentation Files to Review

1. **ESP32_HARDWARE_SPECIFICATIONS.md** - Complete component list & pinouts
2. **ESP32_CLOUD_INTEGRATION_ARCHITECTURE.md** - Python code for cloud processing
3. **ESP32_INTEGRATION_PLAN.md** (existing) - Comprehensive reference
4. **ESP32_INTEGRATION_QUICK_REFERENCE.md** (existing) - Code snippets

---

## SUPPORT & DEBUGGING

### Common Questions

**Q: Can I run facial detection directly on ESP32?**  
A: No. ESP32 has 160 KB RAM. Smallest face detection model is 5 MB. Impossible.

**Q: What if WiFi drops?**  
A: Firmware automatically reconnects. Cloud monitoring detects offline status.

**Q: Can I use 5GHz WiFi?**  
A: No. ESP32 only supports 2.4 GHz band.

**Q: What's the maximum range?**  
A: 50-100 meters line-of-sight. Use WiFi extender if needed.

**Q: Can I use 1 ESP32 with 2 cameras?**  
A: Theoretically possible with multiplexer but NOT recommended. Stick with 2 separate ESP32 units.

**Q: What if I have poor internet upload speed?**  
A: MJPEG bandwidth is 2.4 Mbps. If upload < 10 Mbps: system works fine. If < 2 Mbps: may drop frames.

---

## YOUR PROJECT IS READY FOR:

✅ Real-time 2-camera surveillance  
✅ Cloud-based facial recognition  
✅ Multi-camera person tracking  
✅ Alert generation and dashboard  
✅ Mobile app notifications  
✅ Historical audit trail (Supabase)  

**Go build it! 🚀**

