/**
 * esp32cam_eyedentify_simple.ino
 * ================================
 * Compatible with: ESP32 Arduino core 1.0.6 AND 2.x
 * Board: AI Thinker ESP32-CAM
 *
 * NO ESP-WHO dependency. Face detection is handled entirely
 * by the EYE-DENTIFY Python backend (which has full OpenCV +
 * deep learning) — this is better accuracy anyway.
 *
 * This sketch:
 *   1. Captures a JPEG frame every CAPTURE_INTERVAL_MS ms
 *   2. POSTs it to /api/esp32/frame on your backend
 *   3. Handles WiFi drops with auto-reconnect
 *   4. Blinks the LED on each successful upload
 *
 * SETUP:
 *   1. Fill in WIFI_SSID, WIFI_PASSWORD, SERVER_HOST, SERVER_PORT
 *   2. Tools → Board → AI Thinker ESP32-CAM
 *   3. GPIO0 → GND before upload, remove after, press RESET
 */

#include "esp_camera.h"
#include "WiFi.h"
#include "WiFiClient.h"

// ─── Configuration ────────────────────────────────────────────────────────────
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"

// Cloud Server Setup:
// 1. Deploy to Google Cloud OR Google Colab
// 2. If using GCP: use the External IP and Port 8000
// 3. If using Colab: use the ngrok URL (e.g. xxxx.ngrok-free.app) and Port 80
#define SERVER_HOST         "YOUR_CLOUD_OR_NGROK_URL"    // ← change this
#define SERVER_PORT         80                            // 8000 for GCP, 80 for ngrok
#define UPLOAD_PATH         "/api/esp32/frame"
#define CAMERA_ID           "esp32-cam-01"

// How often to capture and send (milliseconds)
// 3000 = one frame every 3 seconds (good starting point)
// 1000 = one frame per second (if your network can handle it)
#define CAPTURE_INTERVAL_MS  3000

// JPEG quality: 10 = best quality / larger file
//               63 = worst quality / smallest file
#define JPEG_QUALITY         12

#define SERIAL_BAUD          115200
#define WIFI_TIMEOUT_MS      15000
#define HTTP_TIMEOUT_MS      8000

// ─── AI Thinker ESP32-CAM Pin Map ────────────────────────────────────────────
#define CAM_PIN_PWDN     32
#define CAM_PIN_RESET    -1
#define CAM_PIN_XCLK      0
#define CAM_PIN_SIOD     26
#define CAM_PIN_SIOC     27
#define CAM_PIN_D7       35
#define CAM_PIN_D6       34
#define CAM_PIN_D5       39
#define CAM_PIN_D4       36
#define CAM_PIN_D3       21
#define CAM_PIN_D2       19
#define CAM_PIN_D1       18
#define CAM_PIN_D0        5
#define CAM_PIN_VSYNC    25
#define CAM_PIN_HREF     23
#define CAM_PIN_PCLK     22
#define FLASH_LED_PIN     4

// ─── Globals ──────────────────────────────────────────────────────────────────
static uint32_t last_capture_ms = 0;
static uint32_t frame_count     = 0;

// ─── Forward declarations ─────────────────────────────────────────────────────
bool camera_init();
bool wifi_connect();
bool wifi_ensure();
bool upload_jpeg(const uint8_t* buf, size_t len);
void blink(int times, int on_ms = 80, int off_ms = 80);

// ═════════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(500);

    Serial.println("\n========================================");
    Serial.println("  EYE-DENTIFY ESP32-CAM Node");
    Serial.println("========================================");

    pinMode(FLASH_LED_PIN, OUTPUT);
    digitalWrite(FLASH_LED_PIN, LOW);

    if (!camera_init()) {
        Serial.println("[FATAL] Camera failed. Check wiring. Halting.");
        while (true) {
            blink(3, 100, 100);
            delay(1000);
        }
    }

    Serial.println("[CAMERA] Initialised OK");

    if (!wifi_connect()) {
        Serial.println("[WARN] No WiFi at boot — will keep retrying in loop.");
    }

    Serial.printf("[CONFIG] Server : http://%s:%d%s\n",
                  SERVER_HOST, SERVER_PORT, UPLOAD_PATH);
    Serial.printf("[CONFIG] Interval: %d ms\n", CAPTURE_INTERVAL_MS);
    Serial.println("[BOOT] Ready. Capturing...\n");
}

// ═════════════════════════════════════════════════════════════════════════════
void loop() {
    // Enforce capture interval
    uint32_t now = millis();
    if ((now - last_capture_ms) < CAPTURE_INTERVAL_MS) {
        delay(50);
        return;
    }
    last_capture_ms = now;

    // Make sure WiFi is alive
    if (!wifi_ensure()) {
        Serial.println("[LOOP] No WiFi — skipping frame.");
        return;
    }

    // Capture frame
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[ERROR] Frame capture failed.");
        return;
    }

    Serial.printf("[FRAME #%lu] size=%u bytes  ", ++frame_count, fb->len);

    bool ok = upload_jpeg(fb->buf, fb->len);

    // ALWAYS return the frame buffer — memory leak if skipped
    esp_camera_fb_return(fb);

    if (ok) {
        Serial.println("→ uploaded OK");
        blink(1, 60, 0);      // single short flash on success
    } else {
        Serial.println("→ UPLOAD FAILED");
        blink(3, 30, 30);     // three quick flashes on error
    }
}

// ─── Camera init ─────────────────────────────────────────────────────────────
bool camera_init() {
    camera_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));

    cfg.ledc_channel  = LEDC_CHANNEL_0;
    cfg.ledc_timer    = LEDC_TIMER_0;
    cfg.pin_d0        = CAM_PIN_D0;
    cfg.pin_d1        = CAM_PIN_D1;
    cfg.pin_d2        = CAM_PIN_D2;
    cfg.pin_d3        = CAM_PIN_D3;
    cfg.pin_d4        = CAM_PIN_D4;
    cfg.pin_d5        = CAM_PIN_D5;
    cfg.pin_d6        = CAM_PIN_D6;
    cfg.pin_d7        = CAM_PIN_D7;
    cfg.pin_xclk      = CAM_PIN_XCLK;
    cfg.pin_pclk      = CAM_PIN_PCLK;
    cfg.pin_vsync     = CAM_PIN_VSYNC;
    cfg.pin_href      = CAM_PIN_HREF;
    cfg.pin_sscb_sda  = CAM_PIN_SIOD;
    cfg.pin_sscb_scl  = CAM_PIN_SIOC;
    cfg.pin_pwdn      = CAM_PIN_PWDN;
    cfg.pin_reset     = CAM_PIN_RESET;
    cfg.xclk_freq_hz  = 20000000;
    cfg.pixel_format  = PIXFORMAT_JPEG;   // JPEG directly — no conversion needed

    if (psramFound()) {
        Serial.println("[CAMERA] PSRAM found — using QVGA + dual buffer");
        cfg.frame_size   = FRAMESIZE_QVGA;  // 320×240 — fast, good enough
        cfg.jpeg_quality = JPEG_QUALITY;
        cfg.fb_count     = 2;               // double-buffer for speed
    } else {
        Serial.println("[CAMERA] No PSRAM — using QVGA single buffer");
        cfg.frame_size   = FRAMESIZE_QVGA;
        cfg.jpeg_quality = 20;              // lower quality to fit in RAM
        cfg.fb_count     = 1;
    }

    if (esp_camera_init(&cfg) != ESP_OK) {
        return false;
    }

    // Sensor tweaks for indoor / variable lighting
    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_whitebal(s, 1);        // auto white balance
        s->set_awb_gain(s, 1);
        s->set_exposure_ctrl(s, 1);   // auto exposure
        s->set_gain_ctrl(s, 1);       // auto gain
        s->set_brightness(s, 1);
        s->set_contrast(s, 1);
        s->set_hmirror(s, 0);
        s->set_vflip(s, 0);
    }
    return true;
}

// ─── WiFi ─────────────────────────────────────────────────────────────────────
bool wifi_connect() {
    Serial.printf("[WIFI] Connecting to %s ", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - start > WIFI_TIMEOUT_MS) {
            Serial.println(" TIMEOUT");
            return false;
        }
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[WIFI] Connected — IP: %s  RSSI: %d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
}

bool wifi_ensure() {
    if (WiFi.status() == WL_CONNECTED) return true;
    Serial.println("[WIFI] Lost connection — reconnecting...");
    WiFi.disconnect();
    delay(200);
    return wifi_connect();
}

// ─── HTTP upload using raw WiFiClient ────────────────────────────────────────
// We use WiFiClient directly instead of esp_http_client so this compiles on
// both core 1.0.6 and 2.x without any extra library.
//
// The EYE-DENTIFY backend accepts raw application/octet-stream in the body,
// so we just write a minimal HTTP/1.1 POST — no multipart overhead.
bool upload_jpeg(const uint8_t* buf, size_t len) {
    WiFiClient client;
    client.setTimeout(HTTP_TIMEOUT_MS / 1000);   // setTimeout takes seconds

    if (!client.connect(SERVER_HOST, SERVER_PORT)) {
        Serial.printf("[HTTP] Cannot connect to %s:%d\n", SERVER_HOST, SERVER_PORT);
        return false;
    }

    // Build HTTP request headers
    String headers = "";
    headers += "POST ";   headers += UPLOAD_PATH;   headers += " HTTP/1.1\r\n";
    headers += "Host: ";  headers += SERVER_HOST;   headers += "\r\n";
    headers += "Content-Type: application/octet-stream\r\n";
    headers += "X-Camera-ID: ";  headers += CAMERA_ID;  headers += "\r\n";
    headers += "ngrok-skip-browser-warning: 1\r\n"; // Required for Colab/ngrok
    headers += "Content-Length: ";
    headers += String(len);
    headers += "\r\n";
    headers += "Connection: close\r\n";
    headers += "\r\n";

    // Send headers
    client.print(headers);

    // Stream JPEG body in 1 KB chunks to avoid large heap allocation
    const size_t CHUNK = 1024;
    size_t offset = 0;
    while (offset < len) {
        size_t to_send = min(CHUNK, len - offset);
        size_t sent    = client.write(buf + offset, to_send);
        if (sent == 0) {
            Serial.println("[HTTP] Write error mid-stream.");
            client.stop();
            return false;
        }
        offset += sent;
    }

    // Read response (wait up to HTTP_TIMEOUT_MS)
    uint32_t t0  = millis();
    String   line = "";
    int      status_code = 0;
    bool     got_status  = false;

    while (client.connected() || client.available()) {
        if (millis() - t0 > (uint32_t)HTTP_TIMEOUT_MS) {
            Serial.println("[HTTP] Response timeout.");
            break;
        }
        if (!client.available()) { delay(10); continue; }

        char c = client.read();
        if (c == '\n') {
            if (!got_status && line.startsWith("HTTP/")) {
                // e.g. "HTTP/1.1 200 OK"
                status_code = line.substring(9, 12).toInt();
                got_status  = true;
                Serial.printf("[HTTP] Status: %d\n", status_code);
            }
            if (line.length() <= 1) break;  // blank line = end of headers
            line = "";
        } else if (c != '\r') {
            line += c;
        }
    }

    client.stop();
    return (status_code >= 200 && status_code < 300);
}

// ─── LED helper ───────────────────────────────────────────────────────────────
void blink(int times, int on_ms, int off_ms) {
    for (int i = 0; i < times; i++) {
        digitalWrite(FLASH_LED_PIN, HIGH);
        delay(on_ms);
        digitalWrite(FLASH_LED_PIN, LOW);
        if (off_ms > 0) delay(off_ms);
    }
}
