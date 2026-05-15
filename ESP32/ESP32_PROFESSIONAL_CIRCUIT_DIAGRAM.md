# ESP32-CAM Dual Camera System - Professional Circuit Diagram

**Date:** April 17, 2026  
**Design Tool:** Cirkit Design / Fritzing Compatible  
**Status:** Production Ready Circuit Diagram

---

## 🔌 CIRCUIT DIAGRAM - Setup & Operation

### **SETUP PHASE - Programming (Temporary Configuration)**

```
                            COMPUTER
                          USB Port
                             │
                             │ USB Cable
                             ↓
                    ┌─────────────────────┐
                    │  CH340G Programmer  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ 1: GND    ●──┼──┼─ Black
                    │  │ 2: VCC    ●──┼──┼─ Red
                    │  │ 3: RXD    ●──┼──┼─ Green
                    │  │ 4: TXD    ●──┼──┼─ Yellow
                    │  │ 5: DTR    ●──┼──┼─ Orange
                    │  └───────────────┘  │
                    └─────────────────────┘
                      │   │   │   │   │
                      │   │   │   │   └──────┐
                      │   │   │   └─────────┐│
                      │   │   └────────────┐││
                      │   └───────────────┐│││
                      └──────────────────┐││││
                                        ↓↓↓↓↓
                         ┌────────────────────────────┐
                         │   ESP32-CAM Board #1       │
                         │                            │
                         │   ┌──────────────────────┐ │
                         │   │  AI Thinker          │ │
                         │   │  ESP32-CAM v1.1      │ │
                         │   └──────────────────────┘ │
                         │                            │
                         │  Pin Row 1:                │
                         │  GND(●)─Black────────────┐│
                         │  U0R(●)─Green────────────┐│
                         │  5V (●)─Red──────────────┐│
                         │                          │││
                         │  Pin Row 2:              │││
                         │  IO0(●)─Orange─────────┐ │││
                         │  U0T(●)─Yellow────────┐ │ │││
                         │  IO13(●)              │ │ │││
                         │                       │ │ │││
                         │              ↑────────┘ │ │││
                         │              │  GND ────┘ │││
                         │              │  RXD ──────┘││
                         │              │  TXD ───────┘│
                         │              │  BOOT ──────┘
                         │
                         │  ┌─────────────────────┐
                         │  │   OV2640 Camera     │
                         │  │  (24-pin Ribbon)    │
                         │  │  Inside Board       │
                         │  └─────────────────────┘
                         │
                         └────────────────────────────┘

   REPEAT FOR ESP32-CAM #2:
   (Disconnect CH340G after #1, then connect to #2)
```

---

### **OPERATION PHASE - Streaming (Final Configuration)**

```
═══════════════════════════════════════════════════════════════════

                    CONFIGURATION A: CAMERA 1
                    
                    ┌─────────────────────┐
                    │  USB Power Supply   │
                    │     5V / 2A #1      │
                    │                     │
                    │  AC Input: 100-240V │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ USB-A Plug    │  │
                    │  │               │  │
                    │  │ +5V (●) Red ──┼──┼─────┐
                    │  │ GND (●) Black ┼──┼─┐   │
                    │  │               │  │ │   │
                    │  └───────────────┘  │ │   │
                    └─────────────────────┘ │   │
                                            │   │
                      Wires:                │   │
                      • Red: AWG 22, 2m    │   │
                      • Black: AWG 22, 2m  │   │
                                            │   │
                                 ┌──────────┴───┴──────────┐
                                 │                        │
                                 ↓                        ↓
                    ┌────────────────────────────────────────────┐
                    │   ESP32-CAM Board #1 (Streaming)          │
                    │                                            │
                    │   ┌──────────────────────────────────────┐│
                    │   │  POWERED ONLY (CH340G Disconnected)  ││
                    │   └──────────────────────────────────────┘│
                    │                                            │
                    │  Pin Row 1:                                │
                    │  GND ───── ← Black wire from Power ──────┐│
                    │  U0R       (No connection)                ││
                    │  5V  ───── ← Red wire from Power    ──────┤│
                    │                                            ││
                    │  Pin Row 2:                                ││
                    │  IO0       (No connection)                 ││
                    │  U0T       (No connection)                 ││
                    │  IO13      (No connection)                 ││
                    │                                            ││
                    │  ┌─────────────────────────────────────┐  ││
                    │  │   OV2640 Camera Module              │  ││
                    │  │   • 2MP Resolution                  │  ││
                    │  │   • 1600×1200 pixels                │  ││
                    │  │   • MJPEG Encoding                  │  ││
                    │  │   • INTERNAL (24-pin Ribbon)        │  ││
                    │  │   • Power: 300 mA @ 3.3V            │  ││
                    │  └─────────────────────────────────────┘  ││
                    │                                            ││
                    │  ┌─────────────────────────────────────┐  ││
                    │  │   WiFi Radio (On-Board)             │  ││
                    │  │   • 2.4 GHz 802.11b/g/n             │  ││
                    │  │   • Peak Power: 500 mA @ 3.3V       │  ││
                    │  │   • MJPEG Stream: 30 FPS            │  ││
                    │  │   • Resolution: 1600×1200           │  ││
                    │  │   • Output: Port 81 HTTP            │  ││
                    │  └─────────────────────────────────────┘  ││
                    │                                            ││
                    │  ┌─────────────────────────────────────┐  ││
                    │  │   On-Board Regulator                │  ││
                    │  │   • Input: 5V (USB)                 │  ││
                    │  │   • Output: 3.3V to ESP32           │  ││
                    │  │   • Current: 500 mA max             │  ││
                    │  └─────────────────────────────────────┘  ││
                    │                                            ││
                    │  CURRENT BUDGET:                           ││
                    │  ├─ Camera: 300 mA                        ││
                    │  ├─ WiFi Idle: 150 mA                     ││
                    │  ├─ WiFi TX: 400 mA                       ││
                    │  ├─ CPU: 80 mA                            ││
                    │  └─ Total Peak: 1200 mA ← Fits in 2A ✓   ││
                    │                                            ││
                    │  MQTT Data Stream:                         ││
                    │  http://192.168.x.x:81/stream ────────────┼┼─→ WiFi
                    │                                            ││
                    └────────────────────────────────────────────┘│
                                                                  │
                                  REPEAT IDENTICAL FOR CAMERA 2: │
                                                                  │
                    ┌─────────────────────┐                       │
                    │  USB Power Supply   │◄──────────────────────┘
                    │     5V / 2A #2      │
                    │                     │
                    │  AC Input: 100-240V │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ USB-A Plug    │  │
                    │  │               │  │
                    │  │ +5V (●) Red ──┼──┼────────┐
                    │  │ GND (●) Black ┼──┼──┐     │
                    │  │               │  │  │     │
                    │  └───────────────┘  │  │     │
                    └─────────────────────┘  │     │
                                             │     │
                                  ┌──────────┴─────┴──────────┐
                                  │                          │
                                  ↓                          ↓
                    ┌────────────────────────────────────────────┐
                    │   ESP32-CAM Board #2 (Streaming)          │
                    │                                            │
                    │   ┌──────────────────────────────────────┐│
                    │   │  POWERED ONLY (CH340G Disconnected)  ││
                    │   └──────────────────────────────────────┘│
                    │                                            │
                    │  Pin Row 1:                                │
                    │  GND ───── ← Black wire from Power        ││
                    │  U0R       (No connection)                ││
                    │  5V  ───── ← Red wire from Power   ───────┤│
                    │                                            ││
                    │  ┌─────────────────────────────────────┐  ││
                    │  │   OV2640 Camera Module              │  ││
                    │  │   • Identical to Camera #1          │  ││
                    │  └─────────────────────────────────────┘  ││
                    │                                            ││
                    │  ┌─────────────────────────────────────┐  ││
                    │  │   WiFi Radio (On-Board)             │  ││
                    │  │   • Identical to Camera #1          │  ││
                    │  │   • Independent Stream: Port 81     │  ││
                    │  └─────────────────────────────────────┘  ││
                    │                                            ││
                    │  MQTT Data Stream:                         ││
                    │  http://192.168.x.x:81/stream ────────────┼┼─→ WiFi
                    │                                            ││
                    └────────────────────────────────────────────┘│
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    │
                    │ Both Cameras Stream Over Same WiFi Network
                    │ (Separate IP addresses, independent streams)
                    │
                    ↓
        ╔═══════════════════════════════════════╗
        ║         WiFi Router 2.4GHz           ║
        ║     (192.168.0.1 or similar)         ║
        ║                                       ║
        ║   Supports 2× Simultaneous Streams:   ║
        ║   • Camera 1 IP: 192.168.0.100       ║
        ║   • Camera 2 IP: 192.168.0.101       ║
        ║                                       ║
        ║   Bandwidth Required:                 ║
        ║   • 1600×1200 MJPEG @ 30 FPS ≈ 10Mbps│
        ║   • Both cameras ≈ 20 Mbps (OK)      ║
        ║                                       ║
        ╚═══════════════════════════════════════╝
                    │
                    │ Ethernet / WiFi
                    ↓
        ╔═══════════════════════════════════════╗
        ║   Cloud Server / Local PC             ║
        ║                                       ║
        ║   YOLOv8 Person Detection            ║
        ║   DeepSORT Multi-Object Tracking     ║
        ║   InsightFace Facial Recognition     ║
        ║   Clothing Color Analysis            ║
        ║   Alert Decision Engine              ║
        ║                                       ║
        ║   Database Storage (Supabase)        ║
        ║   Real-time Dashboard                ║
        ║                                       ║
        ╚═══════════════════════════════════════╝
```

---

## 🎨 WIRING COLOR CODE REFERENCE

### **Standard Electronics Color Code**

```
During Programming (CH340G Connected):
───────────────────────────────────────
⚫ Black:  Ground (GND) - 0V Reference [CRITICAL FIRST]
🔴 Red:   Power (VCC) - 5V Supply
🟡 Yellow: Serial TX - Data transmission (CH340G→ESP32)
🟢 Green:  Serial RX - Data reception (CH340G←ESP32)
🟠 Orange: Control - Boot mode select (IO0)

During Operation (Power Supply Connected):
──────────────────────────────────────────
⚫ Black:  Ground (GND) - 0V Reference
🔴 Red:   Power (5V) - Main power supply
(Yellow, Green, Orange not used - CH340G disconnected)
```

---

## 📋 COMPONENT SPECIFICATIONS

### **1. ESP32-CAM Board (Qty: 2)**

```
┌──────────────────────────────────────────────────────┐
│ SPECIFICATIONS                                       │
├──────────────────────────────────────────────────────┤
│ Microcontroller:    ESP32 (Tensilica Xtensa 32)    │
│ Processor Cores:    2× @ 240 MHz each               │
│ RAM:                160 KB                          │
│ Flash Storage:      4 MB                            │
│ WiFi:              802.11 b/g/n @ 2.4 GHz          │
│ Bluetooth:         v4.2 LE                          │
│                                                     │
│ Camera Module:      OV2640                          │
│ Resolution:        2 MP (1600×1200)                 │
│ Interface:         SCCB (I²C variant)              │
│ Encoding:          JPEG, MJPEG                      │
│ Frame Rate:        30 FPS @ 1600×1200              │
│                                                     │
│ Power Pins:        5V input, 3.3V output           │
│ Current (Idle):    80 mA                            │
│ Current (Camera):  300 mA @ 3.3V                    │
│ Current (WiFi):    150 mA (idle) → 500 mA (TX)     │
│                                                     │
│ Operating Temp:    -40°C to +85°C                  │
│ Board Size:        ~27mm × 40mm                     │
│                                                     │
│ Boot/UART Pins:                                    │
│ • GND (Ground)                                     │
│ • 5V (Power)                                        │
│ • U0R (GPIO3 - UART RX)                            │
│ • U0T (GPIO1 - UART TX)                            │
│ • IO0 (GPIO0 - Boot Mode Select)                   │
│                                                     │
└──────────────────────────────────────────────────────┘
```

### **2. CH340G USB-TTL Programmer**

```
┌──────────────────────────────────────────────────────┐
│ SPECIFICATIONS                                       │
├──────────────────────────────────────────────────────┤
│ Chip:              CH340G Serial Converter           │
│ Function:          USB ↔ UART (Serial)              │
│ USB Speed:         Full Speed (12 Mbps)             │
│ Baud Rates:        110 ~ 2,000,000 bps              │
│ Standard Rates:    9600, 19200, 38400, 115200 bps  │
│                                                     │
│ Voltage Levels:                                    │
│ • USB: 5V (from computer)                           │
│ • UART: 3.3V ~ 5V (selectable)                      │
│                                                     │
│ Pinout:                                            │
│ • GND (Ground Reference)                           │
│ • VCC (5V from USB)                                │
│ • TXD (Data OUT to ESP32)                          │
│ • RXD (Data IN from ESP32)                         │
│ • DTR (Reset/Boot control)                         │
│                                                     │
│ Connector:         USB Type-A (to Computer)         │
│ Cable Length:      1-2 meters recommended           │
│ Operating Temp:    0°C to 50°C                      │
│                                                     │
│ Cost:             ~$2-4 USD                         │
│ Availability:     Very common, widespread           │
│                                                     │
└──────────────────────────────────────────────────────┘
```

### **3. USB Power Supply 5V 2A (Qty: 2)**

```
┌──────────────────────────────────────────────────────┐
│ SPECIFICATIONS                                       │
├──────────────────────────────────────────────────────┤
│ Input:             AC 100-240V @ 50-60 Hz           │
│ Output:            DC 5.0V ± 0.5V                   │
│ Max Current:       2.0 Amps (2000 mA)               │
│ Max Power:         10 Watts                         │
│                                                     │
│ Connector Type:    USB Type-A (Standard)            │
│ Cable Length:      1.5-2.0 meters                   │
│ Connector Pins:                                    │
│ • Pin 1: +5V (Red)                                 │
│ • Pin 2: Data - (Not used in power-only mode)      │
│ • Pin 3: Data + (Not used in power-only mode)      │
│ • Pin 4: GND (Black)                               │
│                                                     │
│ Efficiency:       > 85%                            │
│ Temperature:      -10°C to +50°C                   │
│ Regulation:       ±5% (4.75V - 5.25V)              │
│                                                     │
│ Safety Features:                                   │
│ • Overcurrent protection                           │
│ • Thermal cutoff at 60°C                           │
│ • No-load current: < 50 mA                         │
│                                                     │
│ Certifications:   CE, FCC, RoHS                    │
│ Cost:             ~$6-10 USD                        │
│                                                     │
│ POWER CAPACITY ANALYSIS:                           │
│ • 2A × 5V = 10W total available power              │
│ • ESP32-CAM peak draw: 1.2A = 6W                  │
│ • Margin: 4W (40% headroom) ✓ SAFE                │
│                                                     │
└──────────────────────────────────────────────────────┘
```

### **4. OV2640 Camera Module (Built-in on ESP32-CAM)**

```
┌──────────────────────────────────────────────────────┐
│ SPECIFICATIONS                                       │
├──────────────────────────────────────────────────────┤
│ Sensor:            OV2640 CMOS Image Sensor         │
│ Maximum Resolution: 2 MP (1600×1200 pixels)         │
│ Output Formats:    YUV, RGB, JPEG, MJPEG           │
│                                                     │
│ Optical Format:    1/2.7"                           │
│ Field of View:     ~160° (wide angle)               │
│ Exposure Range:    100 to 10,000 µs                 │
│                                                     │
│ Interface:         SCCB (I²C variant)              │
│ Connection:        24-pin Ribbon Cable (internal)   │
│ Data Bus:          8-bit parallel                   │
│                                                     │
│ Supported Modes:                                   │
│ • VGA (640×480) @ 30 FPS                           │
│ • SVGA (800×600) @ 30 FPS                          │
│ • UXGA (1600×1200) @ 30 FPS ← Default             │
│ • JPEG encoding on-chip                            │
│ • MJPEG (multiple JPEG frames)                      │
│                                                     │
│ Power Supply:      3.3V DC only                     │
│ Power Consumption: 300 mA (typical)                 │
│ Operating Temp:    -30°C to +70°C                  │
│                                                     │
│ Night Vision:      No (requires good lighting)      │
│ Auto Features:     AWB, AGC, AEC supported         │
│                                                     │
│ Mounted:           Inside ESP32-CAM enclosure       │
│ Ribbon Cable:      24-pin FFC connector             │
│ NOT user-removable (integral to board)             │
│                                                     │
└──────────────────────────────────────────────────────┘
```

---

## 🔗 CONNECTION SUMMARY TABLE

### **Setup/Programming Phase**

| From Component | From Pin | To Component | To Pin | Wire Color | Length | Function |
|---|---|---|---|---|---|---|
| CH340G | GND | ESP32-CAM | GND | Black | 15cm | Ground Reference |
| CH340G | VCC | ESP32-CAM | 5V | Red | 15cm | Power Supply |
| CH340G | TXD | ESP32-CAM | U0R | Yellow | 15cm | Serial RX to ESP32 |
| CH340G | RXD | ESP32-CAM | U0T | Green | 15cm | Serial TX from ESP32 |
| CH340G | DTR | ESP32-CAM | IO0 | Orange | 15cm | Boot Mode Control |
| Computer | USB-A | CH340G | USB Port | USB Cable | 2m | Data & Power |

### **Operation Phase (Camera 1 & 2 Identical)**

| From Component | From Pin | To Component | To Pin | Wire Color | Length | Function |
|---|---|---|---|---|---|---|
| USB Power Supply | +5V | ESP32-CAM | 5V | Red | 1-2m | Main Power Input |
| USB Power Supply | GND | ESP32-CAM | GND | Black | 1-2m | Ground Return |
| ESP32-CAM (Internal) | SCCB | OV2640 Module | SCCB | N/A | Ribbon | Camera Control |
| ESP32-CAM (Internal) | Parallel Data | OV2640 Module | Data Bus | N/A | Ribbon | Video Data |
| ESP32-CAM WiFi | Radio Output | WiFi Router | 2.4 GHz | Wireless | - | MJPEG Stream TX |

---

## ⚡ COMPLETE POWER DISTRIBUTION

```
Wall AC (100-240V, 50-60 Hz)
    │
    ├─────────────────┬─────────────────┐
    │                 │                 │
    ↓                 ↓                 ↓
Power Supply #1    Power Supply #2   (Optional: CH340G Power)
(5V @ 2A)          (5V @ 2A)         (During Programming Only)
    │                 │
    ├─ Red (5V)       ├─ Red (5V)
    └─ Black (GND)    └─ Black (GND)
        │                 │
        ↓                 ↓
    ┌─────────────┐   ┌─────────────┐
    │ ESP32-CAM#1 │   │ ESP32-CAM#2 │
    │             │   │             │
    │ ┌─────────┐ │   │ ┌─────────┐ │
    │ │ OV2640  │ │   │ │ OV2640  │ │
    │ │ 300 mA  │ │   │ │ 300 mA  │ │
    │ └─────────┘ │   │ └─────────┘ │
    │             │   │             │
    │ ┌─────────┐ │   │ ┌─────────┐ │
    │ │ WiFi    │ │   │ │ WiFi    │ │
    │ │ 500 mA  │ │   │ │ 500 mA  │ │
    │ │ (peak)  │ │   │ │ (peak)  │ │
    │ └─────────┘ │   │ └─────────┘ │
    │             │   │             │
    │ ┌─────────┐ │   │ ┌─────────┐ │
    │ │ CPU     │ │   │ │ CPU     │ │
    │ │ 160 mA  │ │   │ │ 160 mA  │ │
    │ │ (max)   │ │   │ │ (max)   │ │
    │ └─────────┘ │   │ └─────────┘ │
    │             │   │             │
    │ TOTAL DRAW: │   │ TOTAL DRAW: │
    │ 1200 mA max │   │ 1200 mA max │
    │ < 2000 mA ✓ │   │ < 2000 mA ✓ │
    │             │   │             │
    └─────────────┘   └─────────────┘
         │                 │
         └────────┬────────┘
                  │ Both stream independently
                  │ over WiFi network
                  ↓
            WiFi Router
                  │
                  ↓
         Cloud Server / PC
```

---

## 📐 PHYSICAL LAYOUT & MOUNTING

```
Typical Desktop Setup:

    ┌─────────────────────────────────────┐
    │         Your Computer               │
    │  USB Port                           │
    │  (CH340G connects here temporarily) │
    └─────────────────┬───────────────────┘
                      │
                      │ USB Cable (2m)
                      │
        ┌─────────────────────┐
        │  CH340G Programmer  │  ← Sits on desk/cable tray
        │  (Setup Only)       │    (Disconnect after firmware upload)
        └─────────────────────┘

For Operation:

    ┌─────────────────────────────────────┐
    │      WiFi Router (2.4 GHz)          │
    │   ✓ Centrally located               │
    │   ✓ Line of sight to both cameras   │
    │   ✓ 802.11n for better range        │
    └──────────┬──────────────┬───────────┘
               │              │
         Power #1        Power #2
         (5V 2A)         (5V 2A)
               │              │
        ┌──────┴──────┐  ┌────┴───────┐
        │ Camera #1   │  │ Camera #2  │
        │ Location A  │  │ Location B │
        │             │  │            │
        │ 2m from     │  │ 2m from    │
        │ power       │  │ power      │
        │ supply      │  │ supply     │
        │             │  │            │
        │ WiFi range: │  │ WiFi range:│
        │ ~30m indoor │  │ ~30m indoor│
        │             │  │            │
        │ Receives    │  │ Receives   │
        │ 4G+         │  │ 4G+        │
        │ (strong)    │  │ (strong)   │
        └─────────────┘  └────────────┘

Maximum Distances:
├─ Power Supply to ESP32: 2 meters (voltage drop limitation)
├─ WiFi Router to Camera: 30 meters indoor (802.11n range)
└─ USB Programmer Cable: 2-3 meters (signal integrity)
```

---

## ✅ PRE-ASSEMBLY CHECKLIST

```
Hardware Verification:
□ 2× ESP32-CAM boards (camera ribbon cable installed?)
□ 1× CH340G programmer (with USB cable)
□ 2× USB Power 5V 2A supplies (check AC outlet compatibility)
□ 10+ jumper wires (AWG 22-24)
□ USB-A to Micro-B or USB Type-C cable (for CH340G)

Tools Required:
□ Multimeter (for voltage verification)
□ Soldering iron (optional - can use breadboard initially)
□ Wire strippers
□ Safety glasses
□ Anti-static wrist strap (recommended)

Software:
□ Arduino IDE 2.x installed
□ Board manager: ESP32 by Espressif v2.0+
□ Board selected: "AI Thinker ESP32-CAM"
□ CH340 drivers installed (OS-specific)
```

---

**Created:** April 17, 2026  
**Design Approach:** Professional Circuit Architecture  
**Status:** Production-Ready Schematic ✓
