# ESP32 Dual Camera System - Exact Hardware Components & Specifications

**Date:** April 17, 2026  
**Project:** Surveillance Pipeline - Multi-Camera ESP32 Integration  
**Scope:** 2× ESP32 camera units with cloud-based facial detection

---

## ⚠️ CRITICAL ARCHITECTURAL CLARIFICATION

### Can We Run Facial Detection on ESP32?

**SHORT ANSWER: NO** ❌

**WHY:**
- ESP32 has **160 KB RAM** - insufficient to load any facial detection model
- Smallest face detection model: **5-50 MB** (e.g., MTCNN, RetinaFace)
- ESP32 CPU: **240 MHz** - too slow for real-time inference
- Face embedding (InsightFace): **512D vector** + requires GPU acceleration typically

**Hardware Limitations Table:**

| Resource | Available | Required (Min) | Gap |
|----------|-----------|----------------|-----|
| **RAM** | 160 KB | 5,000 KB | ❌ 31× under-provision |
| **Storage** | 4 MB | 50-100 MB | ❌ 12-25× under-provision |
| **CPU Speed** | 240 MHz | 2,000+ MHz | ❌ 8-10× slower |
| **GPU** | NONE | Required | ❌ NO GPU |

---

### RECOMMENDED ARCHITECTURE (Used in Your Project)

```
EDGE LAYER (ESP32)
├─ OV2640 Camera (capture frames)
├─ MJPEG Encoder (on-chip)
└─ HTTP Server (stream MJPEG)

                  ↓ WiFi MJPEG Stream ↓

CLOUD LAYER (Your Server)
├─ YOLOv8 Person Detection
├─ DeepSORT Tracking
├─ InsightFace Facial Recognition ← **PROCESSED HERE**
├─ Clothing Color Analysis
└─ Alert Decision Engine
```

**This is the ONLY viable approach** for real-time multi-camera surveillance with facial recognition.

---

## EXACT HARDWARE COMPONENTS FOR 2 ESP32 CAMERAS

### OPTION A: Budget-Friendly (Recommended for Prototyping)

#### Per Camera Unit (×2)

| Component | Part Number / Model | Specifications | Source | Cost |
|-----------|-------------------|-----------------|--------|------|
| **Microcontroller Board** | ESP32-CAM (AI Thinker) | 240MHz dual-core, 4MB Flash, 160KB RAM, WiFi 802.11b/g/n | Amazon, AliExpress | $15-20 |
| **Camera Module** | OV2640 | 2MP, JPEG compression, 30fps capability, FOV 90°, Small form factor | Included with ESP32-CAM | Included |
| **USB Serial Programmer** | CH340G (USB-TTL) | 5V/3.3V, auto-reset, standard baud rates | AliExpress | $3-5* |
| **Power Supply** | 5V 500mA USB Adapter | AC-DC converter, USB type, 500mA continuous | Any | $5-10 |
| **Micro USB Cable** | Standard Micro USB | 5V power + data capable | Any | $2-3 |
| **Stability Mount** | Adjustable Bracket | Aluminum/plastic, 1/4" tripod mount | Amazon | $5-8 |
| **Antenna** (Optional) | Ceramic WiFi Antenna | For improved signal (already integrated in ESP32-CAM) | - | - |

**Per-Unit Cost:** $30-50  
**Total for 2 Units:** $60-100  
**Serial Programmer:** $3-5 (use 1 for both boards, or get 2 for $6-10)

---

### OPTION B: Production-Grade (High Reliability)

#### Per Camera Unit (×2)

| Component | Part Number / Model | Specifications | Source | Cost |
|-----------|-------------------|-----------------|--------|------|
| **Microcontroller Board** | ESP32-S3-DevKitC-1-N16R8V | 240MHz, 16MB Flash, 8MB RAM, WiFi + BLE 5.0 | Espressif Official | $25-30 |
| **Camera Module** | OV2640 High Quality | Same as Option A but with better quality lens | Mouser, Digi-Key | $18-25 |
| **Power Supply** | Mean Well RSP-100-5 | Industrial 5V 20A PSU, screw terminals, certified | Mouser, Digi-Key | $35-45 |
| **USB-UART Bridge** | FTDI FT232RL | Professional grade, better stability than CH340 | Mouser, Digi-Key | $10-15 |
| **Network Cable** | Shielded Cat6 Ethernet | For stable power delivery over longer runs | Any | $15-20 |
| **Protective Enclosure** | NEMA 4X Stainless | IP66 rated, weatherproof, professional mounting | Bopla, Rittal | $40-60 |
| **Antenna Module** | Ceramic Antenna 5dBi | High gain external antenna for better signal | Mouser | $15-20 |

**Per-Unit Cost:** $150-180  
**Total for 2 Units:** $300-360

---

## DETAILED COMPONENT SPECIFICATIONS

### 1. ESP32-CAM Microcontroller (Primary)

**Manufacturer:** AI Thinker  
**Part Number:** ESP32-CAM  
**Datasheet:** https://github.com/ai-thinker-open/esp32-cam

**Technical Specs:**
```
Processor:
├─ Dual-core Tensilica Xtensa 32-bit (240 MHz)
│  ├─ CPU 0: For WiFi stack
│  └─ CPU 1: For application code
├─ Architecture: 32-bit RISC
└─ FPU: Single-precision (no double)

Memory:
├─ SRAM: 160 KB (heap)
├─ Flash: 4 MB (for firmware + OTA)
├─ PSRAM: None (this is a limitation)
└─ RTC: 8 KB (survives deep sleep)

Wireless:
├─ WiFi: 802.11 b/g/n (20/40 MHz channel width)
├─ Frequency: 2.4 GHz only
├─ Data Rate: 150 Mbps (theoretical)
├─ Antenna: On-board PCB antenna
└─ Power: 70-100 mW average (streaming)

GPIO:
├─ Digital I/O: 30 pins
├─ ADC: 12-bit, 8 channels
├─ SPI: 3 interfaces (SPI, HSPI, VSPI)
├─ I2C: 2 interfaces
└─ UART: 2 interfaces (TX/RX)

Camera Interface (Parallel):
├─ DCMI (Digital Camera Model Interface)
├─ 8-bit parallel data bus
├─ I2C control (OV2640 registers)
└─ Support: OV2640, OV7725, OV3660, GC2145

Pinout Reference:
├──────────────────────────┐
│    ESP32-CAM Pinout      │
├──────────────────────────┤
│ Power:  5V, GND          │
│ UART:   TXD0, RXD0       │
│ IO0:    Programming mode │
│ IO2:    PSRAM CS (unused)│
│ IO4:    Internal use     │
│ ...                      │
│ See Part 1.2 for camera  │
└──────────────────────────┘
```

**Power Consumption:**
- Idle (WiFi off): 10 mA
- WiFi connected: 50-80 mA
- Streaming MJPEG: 70-150 mA (depends on FPS)
- Peak during boot: 200 mA

**Recommended Power Supply:** 5V minimum 500mA

---

### 2. OV2640 Camera Module

**Manufacturer:** OmniVision  
**Part Number:** OV2640  
**Resolution:** 2048×1536 (2MP) maximum

**Technical Specs:**
```
Sensor:
├─ Type: 1/4-inch CMOS
├─ Pixel Size: 2.0 μm × 2.0 μm
├─ Resolution: 2MP (nominal)
├─ Active Area: 4096×3072 pixels
└─ Format: Bayer pattern

Image Formats:
├─ JPEG (8-bit quality adjustable)
├─ YUV (4:2:2)
├─ RGB565
└─ Raw Bayer

Output Rates:
├─ Max: 30 FPS @ 1600×1200 (UXGA)
├─ Typical: 15 FPS @ 1024×768 (XGA)
├─ Streaming: 10 FPS @ 800×600 (SVGA) ← Recommended for ESP32
└─ Reduced: 5-10 FPS @ Full resolution

Power:
├─ Core: 1.8V / 50mA
├─ I/O: 3.3V / 10mA
└─ Total: ~60mA typical

Interface:
├─ Parallel 8-bit data bus (DVP/DCMI)
├─ I2C control interface (2-wire)
├─ PCLK (pixel clock): ~24 MHz nominal
├─ VSYNC: Frame sync
└─ HREF: Line sync

Video Quality Settings:
├─ Brightness: Adjustable
├─ Contrast: Adjustable
├─ Saturation: Adjustable
├─ Gamma: Adjustable
├─ White balance: Auto/manual
├─ Exposure: Auto/manual
└─ AGC (Auto Gain Control): Yes

Field of View (FOV):
├─ Horizontal: 90°-110° (depends on lens)
├─ Vertical: 70°-120° (depends on lens)
├─ Diagonal: ~125°

Package:
├─ SMD 56-pins
├─ Connected via ribbon cable (typically)
├─ Standard pin headers for IO
└─ Size: ~25mm × 25mm module board
```

**OV2640 Register Control (I2C):**
- I2C Address: 0x30 or 0x60 (depends on SIAO pin)
- Baud Rate: 100 kHz typical
- ~200+ writable registers
- Can adjust resolution, frame rate, quality, etc. via I2C

---

### 3. USB-TTL Serial Programmer (Required for Flashing)

**Popular Options:**

#### A) CH340G (Budget Option)

**Part Number:** CH340G module (with headers)  
**Characteristics:**
- Chip: WinChipHead CH340G
- Interface: USB Type-A to TTL 5V/3.3V
- Auto-reset & DTR handshake
- Works with Arduino IDE
- Cheap but less reliable

**Wiring to ESP32-CAM:**
```
CH340G → ESP32-CAM
├─ GND → GND (ground level matching)
├─ TX → RX (GPIO 3) ← Cross-connect
├─ RX → TX (GPIO 1) ← Cross-connect
├─ 5V → 5V (power)
└─ DTR → GPIO 0 (for auto-reset programming)
```

**Cost:** $3-5

---

#### B) FTDI FT232RL (Professional Option)

**Part Number:** FT232RL module  
**Characteristics:**
- Chip: FTDI FT232RL
- Interface: USB Type-A to TTL 3.3V/5V switchable
- Excellent stability and driver support
- Self-settling of voltage levels
- Industry standard

**Wiring to ESP32-CAM:**
```
FT232RL → ESP32-CAM
├─ GND → GND
├─ TXD → RX (GPIO 3)
├─ RXD → TX (GPIO 1)
├─ VCC → 5V (or 3.3V)
└─ DTR → GPIO 0 (optional, for auto-reset)
```

**Cost:** $10-15

---

### 4. Power Supply (5V 500mA minimum)

**Requirements:**
- Voltage: **5.0V ±5%** (4.75V - 5.25V acceptable)
- Current: **500mA minimum**, 1000mA recommended
- Ripple: <100mV peak-to-peak
- Protection: Over-current, thermal shutdown

**Options:**

#### A) USB Power Adapter (Simplest)

**Spec:** USB-A 5V 2A output  
**Connector:** USB-A to Micro-USB cable  
**Cost:** $5-10  
**For:** Budget prototyping

```
USB Adapter (AC Wall)
├─ Input: 100-240V AC
├─ Output: 5V 2A
└─ Micro USB Connector
    ├─ Red: +5V
    ├─ Black: GND
    └─ Data wires: Usually unconnected
```

#### B) Industrial PSU (Production)

**Spec:** Mean Well RSP-100-5  
**Output:** 5V 20A (100W)  
**Input:** 90-264V AC  
**Features:** Screw terminal, DIN-rail mount, potentiometer adjustment  
**Cost:** $35-50  
**For:** 24/7 continuous operation

---

### 5. Microcontroller Alternative: ESP32-S3

**Manufacturer:** Espressif (Official)  
**Part Number:** ESP32-S3-DevKitC-1-N16R8V

**Advantages Over ESP32-CAM:**
```
Specification         │ ESP32-CAM  │ ESP32-S3    │ Difference
────────────────────────────────────────────────────────────
Flash                 │ 4 MB       │ 16 MB       │ 4× more storage
PSRAM                 │ None       │ 8 MB        │ ✓ External memory
RAM                   │ 160 KB     │ 512 KB      │ 3× more heap
WiFi                  │ 802.11 b/g │ 802.11 b/g  │ Same
Bluetooth             │ No         │ BLE 5.0     │ ✓ New capability
CPU Speed             │ 240 MHz    │ 240 MHz     │ Same
GPIO                  │ 30 pins    │ 45 pins     │ More IO
Camera Support        │ Yes        │ Yes         │ Same
USB-C                 │ No         │ Yes         │ Better charging
Cost                  │ $15-20     │ $25-30      │ ~$10 more
```

**When to Use ESP32-S3:**
- If you need more RAM for buffering
- If you want dual-camera on one ESP32
- If you need Bluetooth for local control
- If you want future-proofing

**When to Use ESP32-CAM:**
- Budget constraints
- Single camera setup
- Only WiFi needed

---

## MULTI-CAMERA SETUP: 2 × ESP32-CAM CONFIGURATION

### Network Architecture

```
Local Network (WiFi 2.4 GHz)

ESP32-CAM #1                          ESP32-CAM #2
├─ IP: 192.168.1.100                ├─ IP: 192.168.1.101
├─ SSID: YourNetwork                 ├─ SSID: YourNetwork
├─ Password: your_password           ├─ Password: your_password
├─ Port: 80                          ├─ Port: 80
├─ Stream: /stream                   ├─ Stream: /stream
└─ Camera: Entrance                  └─ Camera: Corridor

                       ↓ WiFi Frames ↓

Cloud Server (Your Computer)
├─ IP: 192.168.1.50 (typical)
├─ Port: 8080 (Flask API)
├─ Processes both streams
└─ Outputs alerts to dashboard
```

### IP Address Assignment

**Static IP Recommended (for reliability):**

```cpp
// In ESP32 firmware
const IPAddress STATIC_IP(192, 168, 1, 100);      // ESP32-CAM #1
const IPAddress GATEWAY(192, 168, 1, 1);          // Router
const IPAddress SUBNET(255, 255, 255, 0);         // 255.255.255.0
const IPAddress DNS(8, 8, 8, 8);                  // Google Public DNS

WiFi.config(STATIC_IP, GATEWAY, SUBNET, DNS);
WiFi.begin(SSID, PASSWORD);
```

**For ESP32-CAM #2:**
```cpp
const IPAddress STATIC_IP(192, 168, 1, 101);  // ← Change this
// Rest same as above
```

---

## EXACT BILL OF MATERIALS (BOM) - 2 Camera System

### Option A: Budget Setup

| Qty | Component | Part Number | Supplier | Unit Cost | Total |
|-----|-----------|-------------|----------|-----------|-------|
| 2 | ESP32-CAM | AI Thinker | Amazon | $18 | $36 |
| 2 | Micro USB Cable | Generic | Any | $2 | $4 |
| 1 | USB-TTL (CH340G) | CH340G Module | AliExpress | $4 | $4 |
| 2 | 5V Power Adapter | Generic USB 5V 2A | Any | $8 | $16 |
| 2 | Mounting Bracket | Generic Tripod Mount | Amazon | $7 | $14 |
| — | Jumper Wires | Generic | Any | $3 | $3 |
| **TOTAL** | | | | | **$77** |

**Timeline:** 2-3 weeks (if ordering from AliExpress)

---

### Option B: Professional Setup

| Qty | Component | Part Number | Supplier | Unit Cost | Total |
|-----|-----------|-------------|----------|-----------|-------|
| 2 | ESP32-S3-DevKit | ESP32-S3-DevKitC-1-N16R8V | Mouser | $28 | $56 |
| 2 | OV2640 Camera Module | OV2640 High-Quality | Digi-Key | $22 | $44 |
| 1 | USB-UART Bridge | FT232RL Module | Mouser | $12 | $12 |
| 1 | Industrial PSU | Mean Well RSP-100-5 | Digi-Key | $42 | $42 |
| 2 | Shielded Cat6 Cable | Cat6 10m | Any | $15 | $30 |
| 2 | NEMA 4X Enclosure | Bopla FP 1001 | Bopla Online | $55 | $110 |
| 2 | IP67 Cable Gland | PG-9 | Any | $2 | $4 |
| **TOTAL** | | | | | **$298** |

**Timeline:** 1-2 weeks (from authorized distributors)

---

## CONNECTIVITY: STREAMING TO CLOUD

### MJPEG Stream Format

**What ESP32 Sends:**
```
HTTP/1.1 200 OK
Content-Type: multipart/x-mixed-replace; boundary=frame

--frame
Content-Type: image/jpeg
Content-Length: 15234

[JPEG BINARY DATA - 15,234 bytes]
--frame
Content-Type: image/jpeg
Content-Length: 15789

[JPEG BINARY DATA - 15,789 bytes]
--frame
...continues forever...
```

**Bandwidth Calculation:**
```
Frame Size:     ~15-20 KB (MJPEG compressed)
Frame Rate:     10 FPS
Bandwidth:      15 KB × 10 FPS = 150 KB/s = 1.2 Mbps per camera
For 2 cameras:  2.4 Mbps (~30% of typical WiFi capacity)

WiFi 802.11g actual speeds:
├─ Theoretical: 54 Mbps
├─ Practical: 20-40 Mbps
└─ Margin for efficiency: ✓ Adequate for 2 cameras
```

### Network Interface Requirements

**On Cloud Server:**
- Network adapter: Gigabit Ethernet recommended
- Port: 8080+ (Flask API server)
- Bandwidth: 5 Mbps outbound sustained (2× cameras + overhead)

**Router Requirements:**
- WiFi 2.4 GHz 802.11g/n minimum
- Range: 50 meters line-of-sight minimum
- Ability to assign static IPs (DHCP static reservation)
- 5+ GHz optional (can be used for other devices)

---

## COMPLETE WIRING DIAGRAM FOR ESP32-CAM #1

```
┌────────────────────────────────────────────────────────┐
│           ESP32-CAM #1 Hardware Assembly               │
└────────────────────────────────────────────────────────┘

USB Power Adapter (5V 2A)
├─ Red Wire → [5V Pin] ←──────────┐
└─ Black Wire → [GND Pin] ← [GND]─┴──→ Jumper to Ground Bus
                                          (all GND connected)

OV2640 Camera Module
├─ Ribbon Cable → [Reserved Camera Port]
│                 (ribbon slides into slot with click)
└─ Power: 3.3V + GND (via internal ESP32 regulator)

USB-TTL Programmer (for firmware upload ONLY)
├─ GND → [GND Bus]
├─ TX → [RXD Pin (GPIO 3)]
├─ RX → [TXD Pin (GPIO 1)]
├─ 5V → [5V]        [Only during programming]
└─ DTR → [GPIO 0]   [Optionally: auto-reset mode]

                    ↓ After Firmware Loaded ↓

WiFi Connection (Automatic)
├─ Connects to 192.168.1.1 (your router)
├─ Gets IP: 192.168.1.100
├─ Streams MJPEG on port 80
└─ No additional wiring needed
```

---

## MINIMUM NETWORKING SETUP

**What You Need for 2 ESP32-CAM Streaming:**

1. **WiFi Router** (any modern 802.11g/n router)
   - Budget: $30-60
   - Requirement: Must support 2.4 GHz band

2. **Ethernet Connection to Cloud Server** (optional but recommended)
   - Direct: Gigabit Ethernet from router to server
   - Or: WiFi on server (less reliable for surveillance)

3. **Network Cables** (2×)
   - Micro-USB cables for ESP32 power
   - Ethernet cable for server (optional)

4. **Static IP Configuration**
   - ESP32-CAM #1: 192.168.1.100
   - ESP32-CAM #2: 192.168.1.101
   - Cloud Server: 192.168.1.50

---

## FINAL HARDWARE CHECKLIST

### For Assembly & Testing

- [ ] 2× ESP32-CAM boards (check ribbon cable installed correctly)
- [ ] 2× Micro-USB cables
- [ ] 2× USB power adapters (5V 2A each)
- [ ] 1× USB-TTL programmer (CH340G or FT232RL)
- [ ] 1× USB cable (Type-A to micro-USB for programmer)
- [ ] Jumper wires (male-female, ~10 pack)
- [ ] Breadboard (optional, for organizing connections)
- [ ] Multimeter (for testing voltages)

### For Installation

- [ ] 2× Camera mounting brackets
- [ ] 4× Tripod mounts or wall brackets
- [ ] WiFi router with 2.4 GHz band
- [ ] Ethernet cables (optional)
- [ ] Power strips or outlet adapters
- [ ] Cable ties or conduit (for neatness)

---

## SUMMARY: EXACT ANSWER TO YOUR QUESTION

### "What hardware for minimal facial detection on 2 ESP32s?"

**Direct Answer:**
```
❌ You CANNOT run facial detection on ESP32 due to hardware constraints
✅ CORRECT approach:
   - ESP32: Capture + Stream MJPEG only
   - Cloud (your server): Run facial detection + all processing
```

### Minimum Required Hardware for 2-Camera System:

**Essential (must-have):**
1. **2× ESP32-CAM (AI Thinker)** - $18 each = $36
2. **2× USB Power (5V 2A)** - $8 each = $16
3. **1× USB-TTL Programmer** (CH340G) - $4
4. **WiFi Router** (2.4 GHz) - $0 (likely already have)

**Total Minimum: ~$56**

**Recommended (add to above):**
1. **2× Mounting brackets** - $7 each = $14
2. **Jumper wires & micro-USB cables** - $5
3. **1× Industrial PSU** (if 24/7 operation) - $42
4. **Network monitoring tools** - included in Python

**Total Recommended: ~$117**

---

## NEXT STEPS (Implementation Phases)

### Phase 1: Procurement (Week 1)
- [ ] Order 2× ESP32-CAM + USB-TTL (AliExpress) or immediate (Amazon)
- [ ] Prepare 2× power adapters
- [ ] Verify WiFi router available

### Phase 2: Assembly (Week 2)
- [ ] Insert camera ribbons into ESP32-CAM boards
- [ ] Connect USB-TTL to first ESP32-CAM
- [ ] Upload firmware to both boards (using Arduino IDE)
- [ ] Test MJPEG streaming locally (http://192.168.1.100:80/stream)

### Phase 3: Integration (Week 2-3)
- [ ] Update cloud server to receive MJPEG streams
- [ ] Integrate with existing surveillance_backend_pipeline.py
- [ ] Test facial recognition on cloud server
- [ ] Deploy 2nd camera stream

### Phase 4: Operation (Week 3+)
- [ ] Mount cameras in deployment locations
- [ ] Configure static IPs
- [ ] Move cloud server to production
- [ ] Monitor system performance

---

## REFERENCES & DATASHEETS

**ESP32-CAM:**
- GitHub: https://github.com/ai-thinker-open/esp32-cam
- Pinout Diagram: Search "ESP32-CAM pinout" on GitHub

**OV2640 Camera:**
- Datasheet: OmniVision OV2640 (available on manufacturers' sites)
- Register Guide: https://github.com/espressif/esp32-camera

**WiFi Specifications:**
- IEEE 802.11g: ~54 Mbps theoretical, 20-40 Mbps practical
- 2.4 GHz band: Channels 1-13 (US/EU)
- Range: 50-100 meters line-of-sight

**Firmware Examples:**
- ESP-IDF: https://github.com/espressif/esp-idf
- Arduino Core: https://github.com/espressif/arduino-esp32

---

## KEY TAKEAWAYS

1. **Don't run ML on ESP32** - It's physically impossible
2. **ESP32 is a streaming device only** - All processing on cloud
3. **MJPEG over HTTP works well** - Simple, proven, reliable
4. **2 cameras need proper power** - Shared 5V supply recommended
5. **Total system cost: $100-300** - Depending on components
6. **Your existing pipeline handles everything** - Just add MJPEG receiver

**Estimated Implementation Time: 2-3 weeks from scratch**
