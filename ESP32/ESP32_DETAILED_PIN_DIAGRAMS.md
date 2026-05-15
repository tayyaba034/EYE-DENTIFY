# ESP32-CAM Detailed Pin Connection Diagrams

## WIRING DIAGRAM #1: CH340G Programmer to ESP32-CAM (Programming Phase)

```
╔════════════════════════════════════════════════════════════════════╗
║                      CH340G USB-TTL Programmer                    ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │                                                              │  ║
║  │  USB Side:  [USB-A Connector] → to Computer USB Port       │  ║
║  │                                                              │  ║
║  │  Pin Side:                                                 │  ║
║  │  ┌────────────┐                                            │  ║
║  │  │ GND  ●─────┼─── Black Wire ────────→ ESP32 GND        │  ║
║  │  │ VCC  ●─────┼─── Red Wire   ────────→ ESP32 5V         │  ║
║  │  │ TXD  ●─────┼─── Yellow Wire ──────→ ESP32 RXD(U0R)   │  ║
║  │  │ RXD  ●─────┼─── Green Wire  ──────→ ESP32 TXD(U0T)   │  ║
║  │  │ DTR  ●─────┼─── Orange Wire ─────→ ESP32 IO0         │  ║
║  │  └────────────┘                                            │  ║
║  │                                                              │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════════╝
         │  │  │  │  │
         │  │  │  │  └─ Orange (IO0 Programming Mode)
         │  │  │  └──── Green (Receive from ESP32)
         │  │  └─────── Yellow (Send to ESP32)
         │  └────────── Red (5V Power)
         └───────────── Black (Ground)
                         │
        ╔════════════════╩════════════════════════════════════════╗
        ║           ESP32-CAM #1 (or #2) - During Setup         ║
        ║                                                         ║
        ║  Side View (Top):                                     ║
        ║  ┌──────────────────────────────────────────────┐    ║
        ║  │ GND    U0R    5V      ← Top Row             │    ║
        ║  │ (●)    (●)    (●)                           │    ║
        ║  │  ↓     ↓      ↓                             │    ║
        ║  │ Black Yellow  Red     ← From CH340G        │    ║
        ║  │                                              │    ║
        ║  │ IO0    U0T    IO13    ← 2nd Row            │    ║
        ║  │ (●)    (●)    (●)                           │    ║
        ║  │  ↑     ↓                                     │    ║
        ║  │  Orange Green ← From CH340G                │    ║
        ║  │                                              │    ║
        ║  │  [OV2640 Camera Ribbon Cable - Inside]     │    ║
        ║  │  [Not touched during setup]                │    ║
        ║  └──────────────────────────────────────────────┘    ║
        ║                                                         ║
        ║  Pin Assignment:                                      ║
        ║  • GND    = Ground (establish FIRST)                 ║
        ║  • 5V     = Power input from CH340G                  ║
        ║  • U0R    = UART RX (receives from CH340G TXD)      ║
        ║  • U0T    = UART TX (sends to CH340G RXD)           ║
        ║  • IO0    = Boot/Programming mode selector           ║
        ║                                                         ║
        ╚═════════════════════════════════════════════════════════╝
```

---

## WIRING DIAGRAM #2: Power Supply to ESP32-CAM (Operation Phase)

```
╔════════════════════════════════════════════════════════════════════╗
║                 USB Power Supply 5V 2A #1 (or #2)                ║
║                                                                    ║
║  AC Input: 100-240V (Wall Socket)                               ║
║       │                                                           ║
║       ↓                                                           ║
║  ┌──────────────────────────────┐                               ║
║  │  AC to DC Converter          │                               ║
║  │  (Rectifier & Voltage Reg.)  │                               ║
║  └──────────────────────────────┘                               ║
║       │       │                                                 ║
║       ↓       ↓                                                 ║
║   ┌───────────────┐                                            ║
║   │ USB Port Type-A                                            ║
║   │                                                            ║
║   │  Pin 1: +5V (Red)  ──────┐                               ║
║   │  Pin 2: Data -          (Not used in power-only setup)    ║
║   │  Pin 3: Data +          (Not used in power-only setup)    ║
║   │  Pin 4: GND (Black) ────┐                                ║
║   │                          │                                ║
║   └───────────────┘          │                                ║
║                              │                                ║
║        Red Wire (AWG 22): +5V│                                ║
║        Black Wire (AWG 22): GND│                              ║
║                              │                                ║
║         Max Length: 2 meters (beyond this = voltage drop)    ║
║                              │                                ║
║                    ╔═════════╩═════════╗                      ║
║                    ║                   ║                      ║
║                    ↓                   ↓                      ║
║                   (●)                 (●)                     ║
║                    │                   │                      ║
║  ╔═════════════════════════════════════════════════════════╗  ║
║  ║    ESP32-CAM #1 (During Operation - Powered Only)      ║  ║
║  ║                                                          ║  ║
║  ║   Top Row (Power Delivery):                            ║  ║
║  ║   ┌─────────────────────────────────────────────────┐  ║  ║
║  ║   │ GND      U0R      5V ← Red wire connects here  │  ║  ║
║  ║   │ (●)      (●)      (●)                          │  ║  ║
║  ║   │  ↑                 ↑                            │  ║  ║
║  ║   │  │                 │                            │  ║  ║
║  ║   │  Black ────────────┤ Red                        │  ║  ║
║  ║   │  wire              wire                         │  ║  ║
║  ║   │                    (Power only - no CH340G)     │  ║  ║
║  ║   │                                                  │  ║  ║
║  ║   │ IO0      U0T       IO13 ← No connections here  │  ║  ║
║  ║   │ (●)      (●)       (●)                          │  ║  ║
║  ║   │                                                  │  ║  ║
║  ║   └─────────────────────────────────────────────────┘  ║  ║
║  ║                                                          ║  ║
║  ║   Internal:                                            ║  ║
║  ║   ├─ OV2640 Camera Module (24-pin ribbon) - powered   ║  ║
║  ║   │                                                    ║  ║
║  ║   ├─ WiFi Radio (on-board) - powered                 ║  ║
║  ║   │   Draws: 150 mA (idle) to 500 mA (TX peak)      ║  ║
║  ║   │                                                    ║  ║
║  ║   ├─ Dual-Core CPU (240 MHz each) - powered          ║  ║
║  ║   │   Draws: 80 mA (idle) to 160 mA (active)        ║  ║
║  ║   │                                                    ║  ║
║  ║   └─ Voltage Regulator                               ║  ║
║  ║       Input: 5V DC from USB ┐                         ║  ║
║  ║       Output: 3.3V DC to ESP32 ┘                     ║  ║
║  ║                                                          ║  ║
║  ║   Operation:                                           ║  ║
║  ║   1. Power connected → ESP32 boots                    ║  ║
║  ║   2. Firmware loads → WiFi initializes                ║  ║
║  ║   3. Connects to WiFi SSID                            ║  ║
║  ║   4. Starts MJPEG streaming                           ║  ║
║  ║   5. Camera captures frames continuously              ║  ║
║  ║                                                          ║  ║
║  ╚═════════════════════════════════════════════════════════╝  ║
║                                                                   ║
║  ⚠️  DO NOT CONNECT CH340G DURING THIS PHASE!                   ║
║  ⚠️  Having programmer + power supply connected = voltage spike  ║
║                                                                   ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## WIRING DIAGRAM #3: Complete Dual-Camera System

```
╔════════════════════════════════════════════════════════════════════╗
║           COMPLETE DUAL CAMERA SURVEILLANCE SYSTEM                ║
╚════════════════════════════════════════════════════════════════════╝


SETUP/PROGRAMMING PHASE (Temporarily):
─────────────────────────────────────

┌─────────────────────────────────────────────────────────────┐
│ COMPUTER (USB Connected to CH340G)                          │
│ • Arduino IDE / PlatformIO open                            │
│ • Connected to COM port (e.g., COM3)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │ USB Cable
                   ↓
        ┌──────────────────────┐
        │  CH340G Programmer   │
        │  • 5V powered        │
        │  • Serial connection │
        └──┬──┬──┬──┬──────────┘
           │  │  │  │
        GND│  │  │  └─→ IO0 pin
        5V │  │  └────→ RXD pin
        TXD│  └───────→ RXD pin
        RXD│
           │          ┌─────────────────────────┐
           └─────────→│ ESP32-CAM #1 (Setup)   │
                      │ Being programmed        │
                      │ Uploading firmware      │
                      │ (then disconnect CH340G)│
                      └─────────────────────────┘


OPERATION PHASE (Final Configuration):
─────────────────────────────────────

AC 100-240V     AC 100-240V        BOTH RUNNING SIMULTANEOUSLY:
  │               │
  ↓               ↓
┌──────────┐    ┌──────────┐
│Power 5V  │    │Power 5V  │
│  2A #1   │    │  2A #2   │      • Camera 1: Streaming
└──┬───┬──┘    └──┬───┬──┘        • Camera 2: Streaming
   │   │          │   │           • Both WiFi active
   │   └──GND     │   └──GND       • Both ~900mA draw
   └──5V         └──5V            • Total ~1.8A < 2+2 available
      │              │
      ↓              ↓
   ┌──────────────────────┐      ┌──────────────────────┐
   │ ESP32-CAM #1         │      │ ESP32-CAM #2         │
   │                      │      │                      │
   │ ┌──────────────────┐ │      │ ┌──────────────────┐ │
   │ │ OV2640 Camera    │ │      │ │ OV2640 Camera    │ │
   │ │ 2MP, 1600×1200   │ │      │ │ 2MP, 1600×1200   │ │
   │ │ ~300 mA          │ │      │ │ ~300 mA          │ │
   │ └──────────────────┘ │      │ └──────────────────┘ │
   │                      │      │                      │
   │ WiFi Radio           │      │ WiFi Radio           │
   │ • Idle: 150 mA       │      │ • Idle: 150 mA       │
   │ • TX: 400-500 mA     │      │ • TX: 400-500 mA     │
   │                      │      │                      │
   │ Processor            │      │ Processor            │
   │ • Running: 80-160 mA │      │ • Running: 80-160 mA │
   └──────────────────────┘      └──────────────────────┘
      │ (MJPEG Stream)               │ (MJPEG Stream)
      │ 30 FPS @ 1600×1200           │ 30 FPS @ 1600×1200
      │ Over WiFi                    │ Over WiFi
      │                              │
      └──────────────┬───────────────┘
                     │ WiFi Network (2.4 GHz)
                     ↓
        ╔════════════════════════╗
        ║   WiFi Router         ║
        │ (192.168.x.x)         ║
        ╚════════════════════════╝
              │
              ↓
    ┌─────────────────────┐
    │  Cloud Server       │
    │ • Receives streams  │
    │ • YOLOv8 Detection  │
    │ • Facial Recogn.   │
    │ • Clothing Analysis │
    │ • Alert Decision    │
    └─────────────────────┘
```

---

## REFERENCE TABLE: Pin Locations on ESP32-CAM

```
Physical Board Layout (Top View):

┌────────────────────────────────────────────────────┐
│                  ESP32-CAM Board                   │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │         JTAG / DEBUG HEADER                 │  │
│  │  (For advanced debugging - optional)        │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  Row 1 (Top):                                     │
│  GND    U0R    5V   ← POWER & SERIAL RX          │
│  (●)    (●)    (●)                               │
│                                                    │
│  Row 2:                                           │
│  IO0    U0T    IO13 ← SERIAL TX & BOOT MODE      │
│  (●)    (●)    (●)                               │
│                                                    │
│  Row 3:                                           │
│  IO15   GND    IO14                               │
│  (●)    (●)    (●)                               │
│                                                    │
│  Row 4:                                           │
│  IO2    IO12   IO27                               │
│  (●)    (●)    (●)                               │
│                                                    │
│  Row 5:                                           │
│  IO25   IO26   IO33                               │
│  (●)    (●)    (●)                               │
│                                                    │
│  Row 6 (Bottom):                                  │
│  IO32   IO35   IO34                               │
│  (●)    (●)    (●)                               │
│                                                    │
│              ┌─────────────┐                      │
│              │   CAMERA    │                      │
│              │  CONNECTOR  │                      │
│              │  (24-pin)   │                      │
│              │             │                      │
│        [Camera Module Inside Board]              │
│        [Ribbon Cable Connects to Module]         │
│              │             │                      │
│              └─────────────┘                      │
│                                                    │
│           ╔═══════════════════╗                   │
│           ║  OV2640 Sensor    ║                   │
│           ║  (Under Plastic)  ║                   │
│           ║  2MP Camera       ║                   │
│           ║  1600×1200 px     ║                   │
│           ╚═══════════════════╝                   │
│                                                    │
│  Bottom Label: "AI Thinker ESP32-CAM v1.1"        │
│  (or v1.5 - similar layout)                       │
└────────────────────────────────────────────────────┘

CRITICAL PIN IDENTIFICATION:

┌──────────────────────────────────────────────────┐
│ PIN NAME    │ LABEL ON BOARD │ FUNCTION          │
├──────────────────────────────────────────────────┤
│ Ground      │ GND            │ 0V reference      │
│ Power       │ 5V             │ 5V input          │
│ UART RX     │ U0R            │ Serial receive    │
│ UART TX     │ U0T            │ Serial transmit   │
│ Boot Select │ IO0            │ Programming mode  │
│ GPIO        │ IO2, IO12, etc │ General I/O       │
└──────────────────────────────────────────────────┘

U0R = UART 0 Receive (GPIO3)
U0T = UART 0 Transmit (GPIO1)
IO0 = GPIO0 (used for boot mode selection)
5V = Power input (regulated to 3.3V internally)
GND = Ground (0V reference)
```

---

## SERIAL CONNECTION TEST (After Setup)

```
After uploading code, verify everything works:

Tool: Arduino IDE Serial Monitor
Settings:
├─ Baud Rate: 115200 (must match code)
├─ Line Ending: "Both NL & CR"
└─ Port: COM? (where CH340G was connected)

Expected Output:
─────────────────────
[    0.235] Camera init
[    0.451] Camera ready
[    0.523] WiFi: Scanning...
[    1.234] WiFi: Connecting to "YourSSID"...
[    3.456] WiFi: Connected! IP=192.168.1.100
[    3.512] Starting stream server on port 81
[    3.520] Ready! Access: http://192.168.1.100:81/stream
─────────────────────

Testing Stream:
1. Open browser
2. Go to: http://192.168.1.100:81/stream
3. Should see live MJPEG video from camera
4. Look for motion → verify working

If No Video:
├─ Check WiFi connection (should show Connected)
├─ Check camera cable (should show Camera ready)
├─ Check if URL is correct (get IP from serial monitor)
└─ Check firewall (port 81 may be blocked)
```

---

## COMMON WIRING MISTAKES & FIXES

```
❌ MISTAKE #1: Reversed 5V and GND
   Symptom: ESP32 gets hot, no boot
   Fix: CHECK POLARITY - Red=5V, Black=GND
   Prevention: Test with multimeter first

❌ MISTAKE #2: CH340G Left Connected During Power-Only Phase
   Symptom: ESP32 random resets, WiFi drops
   Fix: DISCONNECT CH340G after uploading code
   Prevention: Use separate power phase

❌ MISTAKE #3: Both Cameras on One Power Supply
   Symptom: Stream lags, random disconnections
   Fix: USE SEPARATE POWER SUPPLIES
   Prevention: Buy 2× supplies (1 per camera)

❌ MISTAKE #4: USB Cable Too Long (>3 meters)
   Symptom: Power supply won't deliver full 2A
   Fix: Use cable <2 meters or shielded cable
   Prevention: Measure before buying cable

❌ MISTAKE #5: No Camera Ribbon Cable
   Symptom: Camera init fails in serial output
   Fix: Insert 24-pin ribbon into camera port
   Prevention: Check camera is installed on board

✅ CORRECT SEQUENCE:
   1. Connect CH340G + USB to Computer
   2. Upload code
   3. Wait 10 seconds
   4. Disconnect CH340G
   5. Connect Power 5V 2A
   6. Look for green LED + boot messages
   7. Camera streams immediately
```

---

**Created:** April 17, 2026  
**For:** ESP32-CAM Surveillance System  
**Status:** Complete Pin & Wiring Reference ✓
