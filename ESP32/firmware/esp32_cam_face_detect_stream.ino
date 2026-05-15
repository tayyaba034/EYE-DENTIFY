#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"

#if __has_include("fd_forward.h") && __has_include("fr_forward.h") && __has_include("img_converters.h") && __has_include("dl_lib.h")
#include "fd_forward.h"
#include "fr_forward.h"
#include "img_converters.h"
#include "dl_lib.h"
#define HAS_FACE_LIBS 1
#else
#define HAS_FACE_LIBS 0
#endif

// -----------------------------------------------------------------------------
// Board profile selection
// Set CAMERA_BOARD_PROFILE to match your ESP32-CAM module wiring.
// For generic ESP32-CAM modules (including many OV3660 variants),
// AI Thinker pin mapping is usually the correct profile.
// -----------------------------------------------------------------------------
#define CAMERA_BOARD_AI_THINKER 0
#define CAMERA_BOARD_ESP_EYE 1
#define CAMERA_BOARD_WROVER_KIT 2

#ifndef CAMERA_BOARD_PROFILE
#define CAMERA_BOARD_PROFILE CAMERA_BOARD_AI_THINKER
#endif

#if CAMERA_BOARD_PROFILE == CAMERA_BOARD_AI_THINKER
// AI Thinker ESP32-CAM pin mapping
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#elif CAMERA_BOARD_PROFILE == CAMERA_BOARD_ESP_EYE
// ESP-EYE pin mapping
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 4
#define SIOD_GPIO_NUM 18
#define SIOC_GPIO_NUM 23

#define Y9_GPIO_NUM 36
#define Y8_GPIO_NUM 37
#define Y7_GPIO_NUM 38
#define Y6_GPIO_NUM 39
#define Y5_GPIO_NUM 35
#define Y4_GPIO_NUM 14
#define Y3_GPIO_NUM 13
#define Y2_GPIO_NUM 34
#define VSYNC_GPIO_NUM 5
#define HREF_GPIO_NUM 27
#define PCLK_GPIO_NUM 25
#elif CAMERA_BOARD_PROFILE == CAMERA_BOARD_WROVER_KIT
// ESP32 WROVER-KIT style pin mapping (common on OV3660 modules)
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 21
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 19
#define Y4_GPIO_NUM 18
#define Y3_GPIO_NUM 5
#define Y2_GPIO_NUM 4
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#else
#error "Unsupported CAMERA_BOARD_PROFILE"
#endif

// Update these values before flashing
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DEVICE_NAME = "ESP32_CAM_01";

WebServer server(80);

struct FaceBox {
  int x;
  int y;
  int w;
  int h;
  float confidence;
};

static FaceBox g_faces[8];
static int g_face_count = 0;
static uint32_t g_last_detect_ms = 0;
static uint32_t g_frame_counter = 0;
static uint32_t g_detect_every_n_frames = 3;
static bool g_is_ov3660 = false;

#if HAS_FACE_LIBS
static mtmn_config_t g_mtmn_config = {0};
#endif

void clearFaces() {
  g_face_count = 0;
}

#if HAS_FACE_LIBS
void runFaceDetection(camera_fb_t* fb) {
  if (!fb) {
    clearFaces();
    return;
  }

  dl_matrix3du_t* rgb = dl_matrix3du_alloc(1, fb->width, fb->height, 3);
  if (!rgb) {
    clearFaces();
    return;
  }

  bool ok = fmt2rgb888(fb->buf, fb->len, fb->format, rgb->item);
  if (!ok) {
    dl_matrix3du_free(rgb);
    clearFaces();
    return;
  }

  box_array_t* boxes = face_detect(rgb, &g_mtmn_config);
  g_face_count = 0;

  if (boxes) {
    int max_faces = boxes->len;
    if (max_faces > 8) {
      max_faces = 8;
    }

    for (int i = 0; i < max_faces; ++i) {
      int x1 = boxes->box[i].box_p[0];
      int y1 = boxes->box[i].box_p[1];
      int x2 = boxes->box[i].box_p[2];
      int y2 = boxes->box[i].box_p[3];

      g_faces[g_face_count].x = x1;
      g_faces[g_face_count].y = y1;
      g_faces[g_face_count].w = x2 - x1;
      g_faces[g_face_count].h = y2 - y1;
      g_faces[g_face_count].confidence = boxes->score[i];
      g_face_count++;
    }

    if (boxes->score) {
      free(boxes->score);
    }
    if (boxes->box) {
      free(boxes->box);
    }
    if (boxes->landmark) {
      free(boxes->landmark);
    }
    free(boxes);
  }

  dl_matrix3du_free(rgb);
  g_last_detect_ms = millis();
}
#endif

void handleRoot() {
  String html;
  html.reserve(600);
  html += "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'/>";
  html += "<title>ESP32 Face Edge Camera</title></head><body>";
  html += "<h2>" + String(DEVICE_NAME) + "</h2>";
  html += "<p><a href='/stream'>MJPEG stream</a></p>";
  html += "<p><a href='/faces'>Face metadata JSON</a></p>";
  html += "<p><a href='/status'>Status JSON</a></p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleStatus() {
  String json;
  json.reserve(256);
  json += "{";
  json += "\"device\":\"" + String(DEVICE_NAME) + "\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"uptime_ms\":" + String(millis()) + ",";
  json += "\"frame_counter\":" + String(g_frame_counter) + ",";
  json += "\"face_count\":" + String(g_face_count) + ",";
#if HAS_FACE_LIBS
  json += "\"face_detection_enabled\":true";
#else
  json += "\"face_detection_enabled\":false";
#endif
  json += "}";

  server.send(200, "application/json", json);
}

void handleFaces() {
  String json;
  json.reserve(1024);
  json += "{";
  json += "\"device\":\"" + String(DEVICE_NAME) + "\",";
  json += "\"timestamp_ms\":" + String(millis()) + ",";
  json += "\"face_count\":" + String(g_face_count) + ",";
  json += "\"faces\":[";

  for (int i = 0; i < g_face_count; ++i) {
    if (i > 0) {
      json += ",";
    }
    json += "{";
    json += "\"bbox\":[" + String(g_faces[i].x) + "," + String(g_faces[i].y) + "," + String(g_faces[i].w) + "," + String(g_faces[i].h) + "],";
    json += "\"confidence\":" + String(g_faces[i].confidence, 3);
    json += "}";
  }

  json += "]}";
  server.send(200, "application/json", json);
}

void handleStream() {
  WiFiClient client = server.client();

  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n";
  response += "Access-Control-Allow-Origin: *\r\n\r\n";

  server.sendContent(response);

  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      delay(10);
      continue;
    }

#if HAS_FACE_LIBS
    if ((g_frame_counter % g_detect_every_n_frames) == 0) {
      runFaceDetection(fb);
    }
#endif

    server.sendContent("--frame\r\n");
    server.sendContent("Content-Type: image/jpeg\r\n");
    server.sendContent("Content-Length: " + String(fb->len) + "\r\n\r\n");
    client.write(fb->buf, fb->len);
    server.sendContent("\r\n");

    esp_camera_fb_return(fb);

    g_frame_counter++;
    delay(70);
  }
}

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QQVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while (true) {
      delay(1000);
    }
  }

  sensor_t* s = esp_camera_sensor_get();
  if (s) {
    g_is_ov3660 = false;
#ifdef OV3660_PID
    if (s->id.PID == OV3660_PID) {
      g_is_ov3660 = true;
    }
#endif

    // OV3660 usually benefits from mirrored + flipped output on WROVER modules.
    if (g_is_ov3660) {
      s->set_vflip(s, 1);
      s->set_hmirror(s, 1);
    }

    s->set_brightness(s, 1);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_framesize(s, FRAMESIZE_QVGA);
  }
}

void setupFaceDetector() {
#if HAS_FACE_LIBS
  g_mtmn_config = mtmn_init_config();
  g_mtmn_config.type = FAST;
  g_mtmn_config.min_face = 80;
  g_mtmn_config.pyramid = 0.707;
  g_mtmn_config.pyramid_times = 4;
  g_mtmn_config.p_threshold.score = 0.6;
  g_mtmn_config.r_threshold.score = 0.7;
  g_mtmn_config.o_threshold.score = 0.7;
#endif
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Starting ESP32-CAM face edge stream...");

  setupCamera();
  setupFaceDetector();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connected. IP: ");
  Serial.println(WiFi.localIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/faces", HTTP_GET, handleFaces);
  server.on("/stream", HTTP_GET, handleStream);

  server.begin();
  Serial.println("Server started.");
  Serial.printf("Stream: http://%s/stream\n", WiFi.localIP().toString().c_str());
  Serial.printf("Faces:  http://%s/faces\n", WiFi.localIP().toString().c_str());

#if CAMERA_BOARD_PROFILE == CAMERA_BOARD_AI_THINKER
  Serial.println("Board profile: AI_THINKER");
#elif CAMERA_BOARD_PROFILE == CAMERA_BOARD_ESP_EYE
  Serial.println("Board profile: ESP_EYE");
#elif CAMERA_BOARD_PROFILE == CAMERA_BOARD_WROVER_KIT
  Serial.println("Board profile: WROVER_KIT");
#endif

  Serial.printf("OV3660 detected: %s\n", g_is_ov3660 ? "yes" : "no");

#if HAS_FACE_LIBS
  Serial.println("Edge face detection: ENABLED");
#else
  Serial.println("Edge face detection: DISABLED (install ESP-WHO compatible face libs)");
#endif
}

void loop() {
  server.handleClient();
}
