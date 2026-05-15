# ESP32-CAM Edge Face Detection Setup (No Recognition)

This guide is aligned with this repository's real entry points and contracts.

## 1. What changes in your architecture

You currently run the main pipeline in:
- `run_surveillance_pipeline.py`
- `surveillance_live_service.py`

New behavior added:
- `face_node_factory.py`
- face mode CLI in both runners: `--face-mode recognition|edge|none`
- edge face metadata input via: `--edge-face-api http://<esp32-ip>`
- multi-camera runner: `run_multicam_surveillance.py`

In `edge` mode, your project uses ESP32 face detection metadata (`/faces`) only. No identity recognition runs in Stage 3A.

## 2. Hardware checklist (single camera first)

1. ESP32-CAM module with OV3660 camera.
2. FTDI/USB-TTL programmer (5V, GND, TX, RX).
3. Stable 5V power (at least 1A recommended for reliability).
4. 2.4 GHz WiFi (ESP32-CAM does not use 5 GHz WiFi).

## 3. Flash firmware to ESP32-CAM

Firmware file in this repo:
- `ESP32/firmware/esp32_cam_face_detect_stream.ino`

Steps:
1. Open Arduino IDE.
2. Install board package: `ESP32 by Espressif Systems`.
3. Board: `AI Thinker ESP32-CAM` (this is the common Arduino profile name for generic ESP32-CAM modules).
4. Upload speed: `115200`.
5. In firmware, set:
   - `WIFI_SSID`
   - `WIFI_PASSWORD`
   - `DEVICE_NAME`
   - `CAMERA_BOARD_PROFILE` (default is already `CAMERA_BOARD_AI_THINKER`)
6. Put board in flash mode:
   - connect `GPIO0` to `GND`
   - press `RST`
7. Upload sketch.
8. Remove `GPIO0 -> GND` jumper.
9. Press `RST` again.
10. Open Serial Monitor at `115200` and note camera IP.

Expected endpoints:
- `http://<ip>/stream` (MJPEG)
- `http://<ip>/faces` (face boxes + confidence)
- `http://<ip>/status`

If camera init fails or image is distorted, switch profile in firmware:
- `CAMERA_BOARD_AI_THINKER` (default)
- `CAMERA_BOARD_WROVER_KIT`
- `CAMERA_BOARD_ESP_EYE`

Then reflash and test `/stream` again.

## 4. Start your Python pipeline with ESP32 (single camera)

Use live service with edge face mode:

```powershell
python surveillance_live_service.py --source http://192.168.1.100/stream --face-mode edge --edge-face-api http://192.168.1.100 --backend deepsort --port 8000
```

Or use file/json runner:

```powershell
python run_surveillance_pipeline.py --source http://192.168.1.100/stream --face-mode edge --edge-face-api http://192.168.1.100 --backend deepsort --headless
```

## 5. Validate integration quickly

1. Open `http://192.168.1.100/status` and confirm `face_detection_enabled` is true.
2. Open `http://192.168.1.100/faces` and check JSON updates when a face appears.
3. Run the Python command above.
4. Confirm output JSON (`runtime/artifacts/latest_pipeline_output.json`) now includes:
   - `face_features[*].face_detected`
   - `face_features[*].face_bbox`
   - `face_features[*].edge_face_source`

## 6. Important behavior notes

1. You are now using edge face detection signal only.
2. `face_score` in edge mode is not identity similarity. It is a detection strength derived from ESP32 confidence + track overlap.
3. Fusion/temporal/alert stages remain unchanged, so threshold tuning may be needed for your environment.

## 7. Move from one camera to two cameras

Flash second ESP32 with same firmware and different `DEVICE_NAME`.

Example:
- cam1 IP: `192.168.1.100`
- cam2 IP: `192.168.1.101`

Run multicam runner:

```powershell
python run_multicam_surveillance.py --sources http://192.168.1.100/stream,http://192.168.1.101/stream --face-mode edge --edge-face-apis http://192.168.1.100,http://192.168.1.101 --backend deepsort
```

Priority failover mode (camera 1 first, camera 2 only on miss):

```powershell
python run_multicam_surveillance.py --sources http://192.168.1.100/stream,http://192.168.1.101/stream --face-mode edge --edge-face-apis http://192.168.1.100,http://192.168.1.101 --backend deepsort --priority-failover --match-signal track
```

Match signal options:
- `track`: switch to next camera only if no confirmed track is found.
- `face`: switch to next camera only if no face detection signal is found.
- `alert`: switch to next camera only if no alert is generated.

Combined output file:
- `runtime/artifacts/latest_multicam_pipeline_output.json`

## 8. Recommended next production step

For dashboard support, run one Flask service per camera now (different ports), then merge to a single unified multicam dashboard API after you validate camera stability and WiFi throughput.

## 9. Troubleshooting

1. ESP32 resets/reboots:
   - power is insufficient; use stronger 5V supply.
2. No WiFi connection:
   - verify SSID/password and 2.4 GHz network.
3. `/faces` empty always:
   - lighting too low or face too small; reduce distance and improve front lighting.
4. Python cannot open stream URL:
   - test in browser first: `http://<ip>/stream`.
5. High latency:
   - keep `FRAMESIZE_QVGA` and detection every 3 frames (default).
