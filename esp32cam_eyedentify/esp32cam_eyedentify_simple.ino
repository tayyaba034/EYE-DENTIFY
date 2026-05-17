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
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ─── Configuration ────────────────────────────────────────────────────────────
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"

// SERVER CONFIGURATION:
// For RunPod:
//   SERVER_HOST: "n63ec2k5oj95bt-8000.proxy.runpod.net" (without http:// or https://)
//   SERVER_PORT: 443 (RunPod HTTPS proxy always runs on port 443)
// For Local PC:
//   SERVER_HOST: "192.168.1.X" (your PC's local IP)
//   SERVER_PORT: 8000
#define SERVER_HOST         "n63ec2k5oj95bt-8000.proxy.runpod.net"
#define SERVER_PORT         443
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

// ─── HTTP upload using HTTPClient & WiFiClientSecure ──────────────────────────
// Handles secure HTTPS connections (port 443) and redirects (301, 307, 308)
// which are required for cloud proxies like RunPod, Google Colab, and ngrok.
bool upload_jpeg(const uint8_t* buf, size_t len) {
    WiFiClientSecure secureClient;
    secureClient.setInsecure(); // Skip certificate verification for simplicity

    HTTPClient http;
    
    // Construct the secure URL
    String url = "https://";
    url += SERVER_HOST;
    if (SERVER_PORT != 443 && SERVER_PORT != 80) {
        url += ":";
        url += String(SERVER_PORT);
    }
    url += UPLOAD_PATH;

    Serial.printf("[HTTP] Connecting to: %s\n", url.c_str());

    if (!http.begin(secureClient, url)) {
        Serial.println("[HTTP] Connection failed at begin.");
        return false;
    }

    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/octet-stream");
    http.addHeader("X-Camera-ID", CAMERA_ID);
    http.addHeader("ngrok-skip-browser-warning", "true");
    http.addHeader("Bypass-Tunnel-Reminder", "true");

    int httpResponseCode = http.POST((uint8_t*)buf, len);
    bool success = false;

    if (httpResponseCode > 0) {
        Serial.printf("[HTTP] Status: %d\n", httpResponseCode);
        if (httpResponseCode >= 200 && httpResponseCode < 300) {
            success = true;
        } else if (httpResponseCode == 301 || httpResponseCode == 302 || httpResponseCode == 307 || httpResponseCode == 308) {
            String newUrl = http.getLocation();
            Serial.printf("[HTTP] Redirecting to: %s\n", newUrl.c_str());
            http.end();
            
            // Try again with the redirect URL
            if (http.begin(secureClient, newUrl)) {
                http.addHeader("Content-Type", "application/octet-stream");
                http.addHeader("X-Camera-ID", CAMERA_ID);
                http.addHeader("ngrok-skip-browser-warning", "true");
                http.addHeader("Bypass-Tunnel-Reminder", "true");
                httpResponseCode = http.POST((uint8_t*)buf, len);
                Serial.printf("[HTTP] Redirect Status: %d\n", httpResponseCode);
                if (httpResponseCode >= 200 && httpResponseCode < 300) {
                    success = true;
                }
            }
        }
    } else {
        Serial.printf("[HTTP] Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }

    http.end();
    return success;
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
