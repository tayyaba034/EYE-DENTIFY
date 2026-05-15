# ESP32-CAM Dual Camera System - Complete Circuit Diagram & Hardware Guide

**Date:** April 17, 2026  
**Project:** Surveillance Pipeline - Multi-Camera Setup  
**Hardware:** 2× ESP32-CAM, USB-TTL Programmer (CH340G), 2× USB Power 5V 2A

---

## 📦 COMPONENT BREAKDOWN - What Each Does & Why It's Needed

### 1. **ESP32-CAM (Qty: 2)**

#### What It Is:
- Microcontroller board with integrated WiFi/Bluetooth and **OV2640 camera module**
- 160 KB RAM, 4 MB Flash storage, dual-core 240 MHz processor
- Can stream MJPEG video over WiFi

#### What It Does:
- **Captures video frames** from the OV2640 camera (2MP, 1600×1200)
- **Encodes frames to JPEG** using on-chip encoder
- **Streams MJPEG** (Motion JPEG = sequence of JPEGs) over HTTP to your cloud server
- Manages WiFi connection
- Can capture up to 30 FPS

#### Why You Need 2:
- **Multi-camera surveillance system** - provides dual-angle monitoring
- Redundancy - if one fails, one continues streaming
- Better coverage of surveillance area
- Enables facial recognition from multiple angles for better accuracy

#### Pinout Reference:
```
ESP32-CAM Pinout:
┌─────────────────────┐
│ GND    U0R    5V    │  (Top row: GND, U0R, 5V)
│ IO0    U0T    IO13  │  (2nd row: IO0, U0T, IO13)
│ IO15   GND    IO14  │  (3rd row: IO15, GND, IO14)
│ IO2    IO12   IO27  │  (4th row: IO2, IO12, IO27)
│ IO25   IO26   IO33  │  (5th row: IO25, IO26, IO33)
│ IO32   IO35   IO34  │  (Bottom row: IO32, IO35, IO34)
└─────────────────────┘

Camera Port (Internal): 24-pin ribbon cable connector
```

---

### 2. **USB-TTL Programmer (CH340G) (Qty: 1)**

#### What It Is:
- **Serial communication converter** - converts USB signals to TTL UART serial signals
- Allows your computer to communicate with ESP32 via USB
- CH340G chip provides the actual USB-to-UART conversion

#### What It Does:
- **Uploads firmware** (MicroPython, Arduino IDE sketches) to ESP32 flash memory
- **Provides debugging** - serial monitor to read debug messages
- **Configures ESP32** - set WiFi credentials, camera parameters
- Establishes programming mode when IO0 is grounded during boot

#### Why You Need It (Only 1 for Both Cameras):
- ESP32 boards don't have built-in USB connectors
- You share this programmer between both ESP32-CAM boards sequentially
- One programmer can upload code to multiple boards
- Essential for initial setup and debugging

#### CH340G Pinout:
```
CH340G Pinout (5 critical pins):
┌───────────┐
│ GND  ●●●  │
│ VCC  ●●●  │
│ RXD  ●●●  │
│ TXD  ●●●  │
│ DTR  ●●●  │ (optional, for auto-reset)
└───────────┘

USB: Standard USB Type-A connector to computer
```

**Why CH340G Specifically?**
- Cheap ($2-4)
- Reliable, widely available
- Works with Arduino IDE, PlatformIO, MicroPython
- Supports both 3.3V and 5V logic (configurable)

---

### 3. **USB Power 5V 2A (Qty: 2)**

#### What It Is:
- AC to DC power adapter
- Input: 100-240V AC from wall outlet
- Output: 5V DC at 2A maximum
- Comes with USB Type-A connector or barrel jack

#### What It Does:
- **Powers the ESP32-CAM** via USB connector or GPIO pins
- **Powers the camera module (OV2640)** - draws ~200-300mA
- **Powers WiFi radio** during transmission - draws ~150-400mA depending on signal strength
- Maintains stable power during video streaming and WiFi operation

#### Why You Need 2 (One Per Camera):
- **Each ESP32-CAM during operation** can draw **500mA-800mA** peak
  - Camera sensor: ~300mA
  - WiFi transmission: ~300-500mA
  - Processor: ~80-150mA
- Sharing 1 power supply would cause:
  - Voltage drops
  - Brownout resets
  - Intermittent streaming failures
  - Connection drops

#### Why 5V 2A Rating:
```
Power Budget for One ESP32-CAM Setup:
├─ OV2640 Camera: 300 mA
├─ WiFi Radio (TX): 300-500 mA
├─ ESP32 Processor: 80-150 mA
├─ LED/Status lights: 20 mA
└─ Margin: 200 mA
────────────────────────────
Total Peak: ~1000-1200 mA ≈ 1.2A

2A rating provides:
✓ Stable operation at peak loads
✓ 60% safety margin (avoiding brownouts)
✓ Allows brief transient spikes
```

---

## 🔌 CIRCUIT DIAGRAM - How Everything Connects

### **Setup Architecture**

```
                    ┌─────────────────────────────────────────────────┐
                    │          YOUR COMPUTER / LAPTOP                 │
                    │  (USB Port connected to CH340G via USB Cable)   │
                    └──────────────────────┬──────────────────────────┘
                                           │
                                           │ USB Cable
                                           ↓
                    ┌─────────────────────────────────────────────────┐
                    │    CH340G USB-TTL Programmer (Only during setup)│
                    │                                                  │
                    │  ┌─────────┐                                    │
                    │  │ GND ●───┼──→ GND Wire (Black)               │
                    │  │ VCC ●───┼──→ 5V Wire (Red)                 │
                    │  │ RXD ●───┼──→ TXD Pin on ESP32              │
                    │  │ TXD ●───┼──→ RXD Pin on ESP32              │
                    │  │ DTR ●───┼──→ IO0 Pin on ESP32 (via 100nF)  │
                    │  └─────────┘                                    │
                    └────────────────────────────────────────────────┘
                           │         │         │          │
         ┌─────────────────┘         │         │          └────────────┐
         │                           │         │                       │
         │                    During Setup:     │                       │
         │                    Disconnect after  │                       │
         │                    uploading code    │                       │
         │                                       │                       │
         ↓                                       ↓                       ↓
    ┌─────────────────────┐            ┌──────────────────────────────────────┐
    │   USB Power 5V 2A   │            │     ESP32-CAM #1 (Camera 1)         │
    │   ──AC 100-240V──   │            │                                      │
    │         │           │            │  ┌────────────────┐                 │
    │         ↓           │            │  │   OV2640       │                 │
    │   ┌─────────────┐   │            │  │  Camera Module │                 │
    │   │ USB Port A  │   │            │  │                │                 │
    │   └──┬─────┬────┘   │            │  └────────────────┘                 │
    │      │     │        │            │                                      │
    │      │     └───────→├─ 5V ───────→ 5V Pin                              │
    │      │              │            │                                      │
    │      └──────────────→├─ GND ──────→ GND Pin                             │
    │                     │            │                                      │
    │                     │            │  (Powered during operation)         │
    └─────────────────────┘            └──────────────────────────────────────┘
                                                 │ (WiFi Stream)
                                                 ↓ (MJPEG frames)
                                         Cloud Server / PC


    ┌─────────────────────┐            ┌──────────────────────────────────────┐
    │   USB Power 5V 2A   │            │     ESP32-CAM #2 (Camera 2)         │
    │   ──AC 100-240V──   │            │                                      │
    │         │           │            │  ┌────────────────┐                 │
    │         ↓           │            │  │   OV2640       │                 │
    │   ┌─────────────┐   │            │  │  Camera Module │                 │
    │   │ USB Port A  │   │            │  │                │                 │
    │   └──┬─────┬────┘   │            │  └────────────────┘                 │
    │      │     │        │            │                                      │
    │      │     └───────→├─ 5V ───────→ 5V Pin                              │
    │      │              │            │                                      │
    │      └──────────────→├─ GND ──────→ GND Pin                             │
    │                     │            │                                      │
    │                     │            │  (Powered during operation)         │
    └─────────────────────┘            └──────────────────────────────────────┘
                                                 │ (WiFi Stream)
                                                 ↓ (MJPEG frames)
                                         Cloud Server / PC
```

---

## 🔗 DETAILED WIRING CONNECTIONS

### **Phase 1: Initial Setup & Programming (CH340G Connected)**

#### From CH340G Programmer to ESP32-CAM:

| CH340G Pin | Wire Color | ESP32-CAM Pin | Purpose |
|-----------|-----------|---------------|---------|
| GND | Black | GND | Ground reference (MUST be first) |
| VCC | Red | 5V | Power for programmer |
| RXD | Green | TXD (U0T) | Receive data (RX from ESP32) |
| TXD | Yellow | RXD (U0R) | Transmit data (TX to ESP32) |
| DTR | Orange | IO0 (via 100nF cap) | Enable programming mode |

**Step-by-Step Wiring:**
```
1. GND (Black wire):    CH340G GND  ←→  ESP32-CAM GND
   (Establish common ground FIRST - this is critical)

2. VCC (Red wire):      CH340G VCC  ←→  ESP32-CAM 5V
   (Provides power to ESP32 during programming)

3. TXD (Yellow):        CH340G TXD  ←→  ESP32-CAM RXD (U0R)
   (CH340G sends → ESP32 receives)

4. RXD (Green):         CH340G RXD  ←→  ESP32-CAM TXD (U0T)
   (CH340G receives ← ESP32 sends)

5. DTR (Orange):        CH340G DTR  ←→  ESP32-CAM IO0
   (Optional: auto-resets into bootloader mode)
```

### **Phase 2: Operation (Power Supply Connected Only)**

Remove CH340G, keep only USB power supply connected:

| USB Power Supply | Wire | ESP32-CAM Pin | Purpose |
|----------------|------|--------------|---------|
| USB +5V (Red) | Red | 5V | Powers ESP32-CAM during streaming |
| USB GND (Black) | Black | GND | Ground reference |

```
USB Power Supply:
    │
    ├─ Red Wire ───→ ESP32-CAM 5V Pin
    │
    └─ Black Wire ──→ ESP32-CAM GND Pin

(No data wires needed during operation - all communication via WiFi)
```

---

## ⚡ POWER REQUIREMENTS & ROUTING

### **Current Draw Analysis**

```
ESP32-CAM Power Budget:
┌────────────────────────────────────────┐
│ Component          │ Current  │ State   │
├────────────────────┼──────────┼─────────┤
│ OV2640 Camera      │ 300 mA   │ Always  │
│ WiFi Radio         │ 150 mA   │ Idle    │
│ WiFi Radio         │ 400 mA   │ TX Peak │
│ ESP32 CPU          │ 80 mA    │ Idle    │
│ ESP32 CPU          │ 160 mA   │ Active  │
│ LED Indicator      │ 20 mA    │ Always  │
├────────────────────┼──────────┼─────────┤
│ TOTAL (idle)       │ ≈550 mA  │ WiFi off│
│ TOTAL (streaming)  │ ≈900 mA  │ Optimal │
│ TOTAL (peak)       │ ≈1200 mA │ Transient
└────────────────────────────────────────┘

2A Power Supply provides:
├─ 2000 mA available
├─ 1200 mA max draw
├─ 800 mA safety margin (40%)
└─ Prevents brownout resets ✓
```

### **Why NOT Share One Power Supply?**

```
If you tried to power BOTH ESP32-CAM units from one 2A supply:

Scenario: Camera 1 + Camera 2 both streaming
├─ Camera 1 needs: 900 mA
├─ Camera 2 needs: 900 mA
├─ Total demand: 1800 mA
├─ Available: 2000 mA
├─ Margin: 200 mA (only 10%)
│
├─ Problem: During WiFi peak transmission
│  ├─ Camera 1 needs: 1000 mA peak
│  ├─ Camera 2 needs: 1000 mA peak
│  ├─ Total demand: 2000 mA peak
│  ├─ Voltage sag: 5V drops to 4.2V
│  ├─ Result: ESP32 brownout reset (minimum = 4.8V)
│  └─ Effect: WiFi disconnection, frozen streams ❌

Solution: 1 Power Supply per Camera
├─ Camera 1: 2A supply (up to 2000 mA available)
├─ Camera 2: 2A supply (up to 2000 mA available)
└─ Both can peak at 1200 mA safely ✓
```

---

## 🛠️ HARDWARE ASSEMBLY CHECKLIST

### **Tools Needed:**
- [ ] Soldering iron + solder (or breadboard + jumper wires for testing)
- [ ] Wire strippers
- [ ] Multimeter (to verify connections)
- [ ] Micro USB cable (for uploading code via CH340G)
- [ ] Jumper wires (AWG 22-24 recommended)

### **Assembly Steps:**

**Step 1: Verify Components**
```
□ 2× ESP32-CAM (check camera ribbon cable is installed)
□ 1× CH340G USB-TTL Programmer (with USB cable)
□ 2× USB Power 5V 2A adapters (with USB Type-A output)
□ Jumper wires or solder + breadboard
```

**Step 2: First ESP32-CAM Setup (Programming Phase)**
```
□ Connect CH340G to Computer via USB
□ Connect CH340G to ESP32-CAM #1 using jumper wires:
  □ GND to GND
  □ VCC to 5V
  □ RXD to TXD (U0T)
  □ TXD to RXD (U0R)
  □ DTR to IO0 (optional for auto-reset)
□ Open Arduino IDE / PlatformIO
□ Select Board: "AI Thinker ESP32-CAM"
□ Select COM port (CH340G will create one)
□ Upload code
□ Wait for success message
□ Disconnect CH340G
```

**Step 3: Power ESP32-CAM #1**
```
□ Connect USB Power 5V 2A Supply:
  □ Red wire to 5V pin
  □ Black wire to GND pin
□ ESP32-CAM should boot
□ Check WiFi indicator lights
□ Verify MJPEG stream starts
```

**Step 4: Repeat for ESP32-CAM #2**
```
□ Connect CH340G to ESP32-CAM #2
□ Upload code (same as #1)
□ Disconnect CH340G
□ Connect USB Power 5V 2A Supply
□ Verify operation
```

---

## 📡 PIN REFERENCE TABLE

### **ESP32-CAM UART Pins (for CH340G Connection)**

| Pin Name | Pin Number | Function | For CH340G |
|----------|-----------|----------|-----------|
| U0R | GPIO3 | UART RX | ← TXD from CH340G |
| U0T | GPIO1 | UART TX | → RXD to CH340G |
| IO0 | GPIO0 | Boot mode select | → DTR from CH340G |
| 5V | Power | 5V input | ← CH340G VCC |
| GND | Ground | Ground reference | ← CH340G GND |

### **Power Delivery Pins**

| Pin Name | Function | Max Current |
|----------|----------|-------------|
| 5V | 5V Input from USB power | 2A (2000 mA) |
| 3V3 | 3.3V regulated output | 500 mA (don't use for camera) |
| GND | Ground (multiple pins available) | N/A |

---

## 🚨 CRITICAL DO's and DON'Ts

### ✅ DO's:
- ✓ Connect **GND first** - establishes reference voltage
- ✓ Use **separate power supplies** for each ESP32-CAM
- ✓ Use **jumper wires** from CH340G during programming only
- ✓ **Disconnect CH340G** after uploading code
- ✓ Use **AWG 22-24 wires** for all connections
- ✓ Keep wires **under 1 meter** to avoid signal degradation
- ✓ **Verify polarity** before connecting power (5V/GND)
- ✓ Check **camera ribbon cable** is fully inserted

### ❌ DON'Ts:
- ✗ Do **NOT** leave CH340G connected while powered (causes conflicts)
- ✗ Do **NOT** reverse 5V and GND (will destroy ESP32)
- ✗ Do **NOT** connect both power supplies to one ESP32
- ✗ Do **NOT** share one 2A supply between both cameras
- ✗ Do **NOT** touch pins while powered
- ✗ Do **NOT** use USB cables longer than 3 meters
- ✗ Do **NOT** solder to ESP32 camera module (use headers instead)
- ✗ Do **NOT** expose ESP32 to moisture without enclosure

---

## 📊 COMPLETE SYSTEM POWER FLOW

```
Wall AC (100-240V)
    │
    ├─→ USB Power Supply #1 ──→ 5V DC 2A ──→ ESP32-CAM #1
    │                                           │
    │                                           ├─→ OV2640 Camera
    │                                           ├─→ WiFi Radio
    │                                           └─→ Processor
    │                                                │
    │                                                ↓ MJPEG Stream
    │                                           Cloud Server
    │
    ├─→ USB Power Supply #2 ──→ 5V DC 2A ──→ ESP32-CAM #2
    │                                           │
    │                                           ├─→ OV2640 Camera
    │                                           ├─→ WiFi Radio
    │                                           └─→ Processor
    │                                                │
    │                                                ↓ MJPEG Stream
    │                                           Cloud Server
    │
    └─→ (Optional) USB Power for CH340G Programmer ← During setup only
                        ↓
                   Computer USB Port
                   (During firmware upload phase only)
```

---

## 🔍 TESTING & VERIFICATION

### **Multimeter Tests (with power supply connected, CH340G disconnected):**

```
Test 1: 5V Rail Voltage
├─ Multimeter on DC Voltage mode
├─ Red probe on ESP32-CAM 5V pin
├─ Black probe on GND pin
├─ Expected: 4.9V - 5.1V
└─ If <4.8V: Power supply may be faulty

Test 2: Ground Continuity
├─ Multimeter on Continuity mode
├─ Test each GND pin
├─ Expected: Beep/low resistance
└─ If no beep: Check wiring

Test 3: Current Draw
├─ Turn off ESP32 (disconnect power)
├─ Insert multimeter in series with red wire
├─ Power back on, wait 10 seconds
├─ Streaming idle: ≈0.55A
├─ During stream: ≈0.9A
└─ Peak: <1.2A (if higher, check for short circuit)
```

---

## 📝 WIRING SUMMARY TABLE

### **Setup Phase (Programming)**
| From | To | Wire Color | Wire Gauge | Length |
|------|----|-----------|-----------|----|
| CH340G GND | ESP32 GND | Black | AWG 24 | 15cm |
| CH340G VCC | ESP32 5V | Red | AWG 24 | 15cm |
| CH340G RXD | ESP32 TXD | Green | AWG 24 | 15cm |
| CH340G TXD | ESP32 RXD | Yellow | AWG 24 | 15cm |
| CH340G DTR | ESP32 IO0 | Orange | AWG 24 | 15cm |

### **Operation Phase (Powered)**
| From | To | Wire Color | Wire Gauge | Length |
|------|----|-----------|-----------|----|
| USB +5V | ESP32 5V | Red | AWG 22 | 1-2m |
| USB GND | ESP32 GND | Black | AWG 22 | 1-2m |

---

## 💡 WHY THIS SPECIFIC HARDWARE?

| Component | Why This Model | Why Not Others |
|-----------|---|---|
| **ESP32-CAM** | On-board OV2640 camera, WiFi built-in, cheap ($18) | ESP32 alone = no camera; other boards = $50+; Raspberry Pi = $35+ with separate camera |
| **CH340G** | Compatible with all OS, cheap ($4), reliable | FT232RL = $12; PL2303 = inconsistent drivers; Arduino upload = uses built-in, can't program external ESP32 |
| **USB 5V 2A** | Perfect power margin per camera, standard size | 1A = brownout; 3A = overkill; barrel jack = proprietary connectors |

---

## 🎯 NEXT STEPS AFTER HARDWARE ASSEMBLY

1. **Upload Firmware** to both ESP32-CAM units using CH340G
2. **Configure WiFi** credentials (SSID, password)
3. **Set Camera Parameters** (resolution 1600×1200, quality 15)
4. **Test Stream** by accessing `http://<esp32-ip>:81/stream` in browser
5. **Connect to Cloud** - stream MJPEG to your surveillance server
6. **Mount Cameras** in desired locations with power wires

---

**Created:** April 17, 2026  
**For:** Surveillance Pipeline Project  
**Status:** Complete Hardware Specification ✓
