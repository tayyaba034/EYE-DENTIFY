/*
  ESP32-CAM AI Thinker (OV3660) → Sentinel Command Dashboard
  https://n63ec2k5oj95bt-8000.proxy.runpod.net/

  Board : AI Thinker ESP32-CAM
  IDE   : Arduino IDE 2.x  |  esp32 board package ≥ 3.0
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

// ─────────────────────────────────────────────
//  EDIT ONLY THESE 2 LINES
// ─────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// ─────────────────────────────────────────────

const char* SERVER_URL  = "https://n63ec2k5oj95bt-8000.proxy.runpod.net/ingest";
const char* CAMERA_ID   = "aithinker-ov3660-01";
const int   TARGET_FPS  = 5;

// These are the fixed internal pins on the AI Thinker PCB — do not change
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

uint32_t frameCounter = 0;
unsigned long lastFrameMs = 0;

void setup() {
  Serial.begin(115200);

  // --- Init Camera ---
  camera_config_t cfg;
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.pin_d0 = Y2_GPIO_NUM;  cfg.pin_d1 = Y3_GPIO_NUM;
  cfg.pin_d2 = Y4_GPIO_NUM;  cfg.pin_d3 = Y5_GPIO_NUM;
  cfg.pin_d4 = Y6_GPIO_NUM;  cfg.pin_d5 = Y7_GPIO_NUM;
  cfg.pin_d6 = Y8_GPIO_NUM;  cfg.pin_d7 = Y9_GPIO_NUM;
  cfg.pin_xclk  = XCLK_GPIO_NUM;
  cfg.pin_pclk  = PCLK_GPIO_NUM;
  cfg.pin_vsync = VSYNC_GPIO_NUM;
  cfg.pin_href  = HREF_GPIO_NUM;
  cfg.pin_pwdn  = PWDN_GPIO_NUM;
  cfg.pin_reset = RESET_GPIO_NUM;
  cfg.pin_sccb_sda = SIOD_GPIO_NUM;
  cfg.pin_sccb_scl = SIOC_GPIO_NUM;
  cfg.xclk_freq_hz = 24000000;   // OV3660 needs 24 MHz
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size   = FRAMESIZE_UXGA;  // 1600x1200 (3MP)
  cfg.jpeg_quality = 10;
  cfg.fb_count     = 2;
  cfg.fb_location  = CAMERA_FB_IN_PSRAM;
  cfg.grab_mode    = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&cfg) != ESP_OK) {
    Serial.println("Camera init failed!");
    return;
  }

  // OV3660 orientation fix
  sensor_t* s = esp_camera_sensor_get();
  s->set_vflip(s, 1);
  s->set_brightness(s, 1);
  s->set_saturation(s, 0);
  Serial.println("Camera ready");

  // --- Connect WiFi ---
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());
  Serial.println("Streaming to Sentinel...");
}

void loop() {
  // Reconnect if WiFi drops
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    delay(2000);
    return;
  }

  // Enforce FPS
  if (millis() - lastFrameMs < (1000 / TARGET_FPS)) return;
  lastFrameMs = millis();

  // Capture frame
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Capture failed");
    return;
  }

  // Send to Sentinel
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;
  http.begin(client, SERVER_URL);
  http.setTimeout(8000);
  http.addHeader("Content-Type",  "image/jpeg");
  http.addHeader("X-Camera-ID",   CAMERA_ID);
  http.addHeader("X-Frame-Index", String(frameCounter));

  int code = http.POST(fb->buf, fb->len);
  Serial.printf("Frame %u — %u bytes — HTTP %d\n", frameCounter, fb->len, code);

  http.end();
  esp_camera_fb_return(fb);
  frameCounter++;
}
