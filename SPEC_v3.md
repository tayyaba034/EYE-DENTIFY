# IoT Surveillance System — Final Production Specification (v3.0)

**Status:** Authoritative — supersedes all prior specifications  
**Version:** 3.0  
**Date:** 2026-05-01  
**Audience:** Firmware engineers, backend engineers, DevOps, QA  
**Rule:** When this document conflicts with any prior spec, audit report, or pipeline document, this document wins. Code is truth; this document defines what code must do.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Edge Device Layer — ESP32-CAM](#2-edge-device-layer)
3. [Backend Architecture](#3-backend-architecture)
4. [Height Estimation Module](#4-height-estimation-module)
5. [Target Profile System](#5-target-profile-system)
6. [End-to-End Pipeline](#6-end-to-end-pipeline)
7. [Fusion Engine](#7-fusion-engine)
8. [Tracking and Re-Identification](#8-tracking-and-re-identification)
9. [Security Architecture](#9-security-architecture)
10. [AI Agents](#10-ai-agents)
11. [Data Models](#11-data-models)
12. [Failure Handling](#12-failure-handling)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Performance Constraints](#14-performance-constraints)
15. [Monitoring and Observability](#15-monitoring-and-observability)
16. [Final Execution Flow](#16-final-execution-flow)

---

## 1. System Overview

### 1.1 Purpose

This system is an IoT-based multi-modal person identification and alert pipeline. An ESP32-CAM device performs edge-level face detection and motion-triggered frame capture. Selected frames are transmitted over WiFi to a backend inference pipeline that performs deep feature extraction (face recognition, clothing analysis, height estimation), multi-attribute fusion, temporal validation, and alert delivery.

The system is designed for fixed-camera installation scenarios where continuous video streaming is impractical due to bandwidth and power constraints. Intelligence is distributed: the edge device filters aggressively, the backend decides authoritatively.

### 1.2 Architecture Split

| Concern | Edge (ESP32-CAM) | Backend (Cloud / Server) |
|---|---|---|
| Motion detection | YES — hardware interrupt + frame diff | NO |
| Face detection | YES — lightweight model (face present/absent) | NO |
| Face recognition | NO | YES — InsightFace buffalo_l |
| Person tracking | NO | YES — DeepSORT |
| Height estimation | NO | YES — YOLOv8-pose |
| Clothing analysis | NO | YES — HSV histogram |
| Fusion scoring | NO | YES — weighted multi-signal |
| Alert decision | NO | YES — temporal validator + alert agent |
| Alert storage | NO | YES — Supabase/Postgres |
| Dashboard API | NO | YES — Flask + Gunicorn |

### 1.3 Data Flow Summary

```
ESP32-CAM
  │ (1) Motion / face trigger
  │ (2) JPEG frame + metadata → HTTPS POST
  ▼
Backend Ingestion Endpoint
  │ (3) Device auth verification
  │ (4) Frame enqueue → Redis stream "frames:incoming"
  ▼
Inference Worker (Process 1, GPU)
  │ (5) YOLO detect → DeepSORT track
  │ (6) Face + clothing + height extraction
  │ (7) Fusion score
  │ (8) Alert candidates → Redis stream "stream:alert_candidates"
  │     Pipeline state → Redis key "pipeline:state" (2s TTL)
  ▼
Alert Decision Worker (Process 2, CPU, singleton)
  │ (9) Temporal validation
  │ (10) Behavioural anomaly scoring
  │ (11) Explainability + audit chain write
  │ (12) Supabase alert write
  ▼
API Server (Process 3, stateless, N replicas)
  │ (13) Authenticated dashboard reads
  │ (14) Real-time state from Redis
  ▼
Operator Dashboard
```

### 1.4 System Invariants

These constraints are non-negotiable and must be preserved across all code changes:

- The ESP32-CAM is the exclusive frame source. The backend does not poll a camera directly unless the system is running in `--dev-mode` with a local webcam override explicitly specified at startup.
- Height estimation is a mandatory subsystem. It is never removed. It is conditionally activated based on calibration state and pose confidence.
- Temporal validation gates alerts. It does not modify fusion scores.
- Fusion is always computed before temporal validation.
- Process 2 (alert decision worker) always runs as a single instance. Horizontal scaling of this process is prohibited.
- JWT authentication is required on all data endpoints before any network exposure beyond localhost.

---

## 2. Edge Device Layer

### 2.1 Hardware

**Device:** ESP32-CAM (AI-Thinker module or equivalent with OV2640 sensor)  
**Processor:** Xtensa LX6 dual-core 240 MHz  
**RAM:** 520 KB SRAM + 4 MB PSRAM  
**Camera:** OV2640, configurable resolution up to 1600×1200  
**Network:** 802.11 b/g/n WiFi  
**Power:** 5V USB or regulated 3.3V; no battery operation assumed in this deployment

### 2.2 What Runs on the ESP32-CAM

#### 2.2.1 Motion Detection

The device performs frame differencing on consecutive grayscale-downsampled frames at 80×60 resolution to detect motion. This runs at 10 FPS regardless of transmission state.

```c
// Pseudocode — motion threshold
#define MOTION_PIXEL_THRESHOLD  25      // pixel intensity delta
#define MOTION_RATIO_THRESHOLD  0.012f  // 1.2% of frame pixels must differ

bool detect_motion(uint8_t *prev_gray, uint8_t *curr_gray, int len) {
    int changed = 0;
    for (int i = 0; i < len; i++) {
        if (abs((int)curr_gray[i] - (int)prev_gray[i]) > MOTION_PIXEL_THRESHOLD)
            changed++;
    }
    return ((float)changed / len) >= MOTION_RATIO_THRESHOLD;
}
```

Motion detection consumes negligible compute at 80×60. It is the primary gating condition before any transmission occurs.

#### 2.2.2 Face Detection

When motion is detected, the device captures a full-resolution frame (640×480) and runs a lightweight face presence detector to determine whether a face is visible before transmitting. This prevents transmitting frames with no useful signal.

**Model:** MTCNN-equivalent TFLite model quantized for ESP32 (INT8), or the ESP-WHO face detection library from Espressif. The model outputs a binary face-present/absent decision and an approximate bounding box. It does NOT perform recognition — that happens entirely on the backend.

If the ESP-WHO face detector is not available for the target firmware version, this step is skipped and all motion-triggered frames are transmitted. This is the fallback, not the preferred path.

#### 2.2.3 Frame Capture and Compression

When both motion and face presence are confirmed (or motion only, in fallback mode), the device captures a JPEG frame at 640×480 with quality factor 85. This produces frames of approximately 25–60 KB depending on scene complexity.

The device does NOT transmit full 1600×1200 frames under any circumstances. The 640×480 resolution is fixed for transmission. Higher resolutions may be used internally for face detection but the transmitted frame is always downsampled to 640×480 before encoding.

#### 2.2.4 Frame Sampling Rate

The device enforces a minimum inter-frame interval of 500 ms (maximum 2 FPS transmission rate) regardless of how frequently motion or face triggers fire. This is a hard rate limit to prevent backend overload on scenes with continuous motion.

During an active alert session (signalled by the backend via MQTT acknowledgement — see Section 2.4), the inter-frame interval is reduced to 200 ms (5 FPS) for the duration of the session, up to a maximum of 30 seconds, after which it reverts to 500 ms.

### 2.3 What the ESP32-CAM Transmits

Each transmission is a single HTTPS POST containing a multipart payload:

```
POST /api/ingest/frame
Content-Type: multipart/form-data

Field: frame        — JPEG bytes (640×480, quality 85)
Field: metadata     — JSON string (see schema below)
```

**Metadata JSON schema:**

```json
{
  "device_id":        "esp32-cam-001",
  "device_hmac":      "<HMAC-SHA256 of frame bytes using device_secret>",
  "timestamp_ms":     1746123456789,
  "trigger":          "face_detected",
  "motion_ratio":     0.043,
  "face_bbox":        [x, y, w, h],
  "face_confidence":  0.87,
  "firmware_version": "3.0.1",
  "sequence_number":  4821
}
```

`trigger` is one of: `face_detected`, `motion_only`, `manual`.  
`face_bbox` is `null` when `trigger` is `motion_only`.  
`device_hmac` is the HMAC-SHA256 of the raw JPEG bytes using the device's pre-shared secret key. The backend verifies this before accepting the frame.

### 2.4 Transmission Method

**Primary channel:** HTTPS POST to the backend ingestion endpoint. TLS 1.2 minimum. Certificate pinning is enabled on the device — the backend certificate's SHA-256 fingerprint is compiled into the firmware.

**Secondary channel (acknowledgement and session control):** MQTT over TLS. The device subscribes to `devices/{device_id}/control`. The backend publishes to this topic to signal:
- `{"cmd": "alert_session_start"}` — reduce inter-frame interval to 200 ms
- `{"cmd": "alert_session_end"}` — revert to 500 ms interval
- `{"cmd": "reboot"}` — device reboots (used for remote firmware update)
- `{"cmd": "calibration_request"}` — device captures and transmits a special calibration frame (see Section 4.3)

**MQTT broker:** Mosquitto running as a sidecar in the backend deployment. Exposed on port 8883 (TLS). The device authenticates to MQTT with its `device_id` as username and its `device_secret` as password.

### 2.5 Failure Behavior

#### 2.5.1 WiFi Disconnection

The device implements exponential backoff reconnection: 1s, 2s, 4s, 8s, 16s, 32s, then fixed 60s retry. During disconnection, motion and face detection continue running. Frames that trigger transmission while disconnected are queued in PSRAM up to a maximum of 8 frames (approximately 400 KB). When connectivity is restored, queued frames are transmitted in sequence. If the queue is full, the oldest frame is dropped.

#### 2.5.2 Backend HTTP Failures

If the backend returns a 5xx response or the connection times out (10 second timeout), the frame is re-queued for retry with a 2-second delay. Maximum 3 retries per frame. After 3 failures the frame is discarded and a transmission failure counter is incremented. If 10 consecutive frames fail to transmit, the device logs a critical error to its serial port and attempts a WiFi reconnection cycle.

#### 2.5.3 Backend Returns 401 or 403

The device credential has been rejected. The device halts transmission, logs the error, and waits for a manual reboot or a remote `reboot` command via MQTT. It does NOT attempt to re-authenticate automatically to prevent credential lockout.

### 2.6 Bandwidth Constraints

Maximum sustained transmission rate: 2 FPS × 50 KB/frame = 100 KB/s = 800 Kbps.  
At 5 FPS alert session rate: 5 × 50 KB = 250 KB/s = 2 Mbps.  
Required uplink bandwidth: 2 Mbps sustained during alert sessions.  
Required uplink bandwidth in idle mode: 800 Kbps.

These values assume typical 640×480 JPEG at quality 85. Scenes with high entropy (crowds, outdoor environments) may produce larger frames. The 640×480 resolution cap is the primary bandwidth control mechanism.

### 2.7 Firmware Deployment

Firmware is compiled with PlatformIO. OTA updates are delivered via the MQTT `reboot` command followed by an HTTP OTA fetch from a versioned firmware URL stored in the device config. The device verifies the downloaded binary's SHA-256 checksum before flashing. Failed OTA reverts to the prior firmware version.

---

## 3. Backend Architecture

### 3.1 Three-Process Model

The backend runs as exactly three distinct process types. These must never be merged into a single process.

#### Process 1 — Inference Worker

**Count:** 1 instance (GPU-bound, cannot be scaled horizontally)  
**Entrypoint:** `python inference_worker.py --backend deepsort`  
**Owns:** Frame ingestion from Redis, YOLO detection, DeepSORT tracking, face extraction, clothing extraction, height estimation, fusion, Re-ID agent  
**Writes:** Pipeline state to Redis key `pipeline:state` (2-second TTL), alert candidates to Redis stream `stream:alert_candidates`  
**GPU:** Exclusively owns all GPU memory. No other process accesses GPU.

#### Process 2 — Alert Decision Worker

**Count:** 1 instance (stateful singleton — enforced by Redis distributed lock)  
**Entrypoint:** `python alert_decision_worker.py`  
**Owns:** Temporal validator state, behavioural anomaly agent, explainability engine, audit log, Supabase writes  
**Reads:** Redis stream `stream:alert_candidates`  
**Writes:** Supabase `alerts` table, local audit chain at `runtime/audit/alert_chain.jsonl`  
**Redis lock key:** `lock:alert_decision_worker` with 30-second TTL, renewed every 10 seconds. If a second instance attempts to start and cannot acquire the lock within 5 seconds, it exits with code 1.

#### Process 3 — API Server

**Count:** N instances (stateless, horizontally scalable)  
**Entrypoint:** `gunicorn -w 4 -b 0.0.0.0:3000 surveillance_live_service:app`  
**Owns:** All HTTP endpoints, dashboard serving, JWT validation  
**Reads:** Redis key `pipeline:state`, Supabase `alerts` table (via `SUPABASE_ANON_KEY`)  
**Does not:** Access GPU, run inference, write to Supabase directly

### 3.2 Frame Ingestion Endpoint

The ingestion endpoint runs inside Process 3. It is the backend's interface to the ESP32-CAM.

```
POST /api/ingest/frame
Authorization: Bearer <device_jwt>
Content-Type: multipart/form-data
```

Processing steps:
1. Validate device JWT (signed with `DEVICE_JWT_SECRET`, separate from operator JWT secret).
2. Extract `device_id` from JWT claims.
3. Parse multipart: extract JPEG bytes and metadata JSON.
4. Verify `device_hmac`: recompute HMAC-SHA256 of JPEG bytes using the device's registered `device_secret` from the device registry table. Reject with 403 if mismatch.
5. Validate `sequence_number` is greater than the last accepted sequence number for this device (stored in Redis key `device:{device_id}:last_seq`). Reject with 409 if replay detected.
6. Write frame to Redis stream `stream:frames:incoming` with fields: `device_id`, `frame_bytes` (base64), `metadata_json`, `received_at`.
7. Return 202 Accepted.

The ingestion endpoint does not perform any inference. It is a secure relay from edge to inference queue.

### 3.3 Redis Schema

```python
# Pipeline state (written by inference worker every processed frame)
redis.setex("pipeline:state", 2, json.dumps({
    "timestamp": float,
    "active_tracks": int,
    "last_frame_device_id": str,
    "motion_ratio": float,
    "alert_candidates_pending": int
}))

# Incoming frames from ESP32
redis.xadd("stream:frames:incoming", {
    "device_id": str,
    "frame_b64": str,           # base64-encoded JPEG
    "metadata": str,            # JSON string
    "received_at": str          # ISO8601
})

# Alert candidates from inference worker
redis.xadd("stream:alert_candidates", {
    "track_id": str,
    "fusion_score": str,
    "height_consistent": str,   # "true" / "false"
    "height_penalty_applied": str,
    "frame_timestamp": str,
    "payload": str              # JSON string, full candidate payload
})

# Device sequence tracking (replay prevention)
redis.set(f"device:{device_id}:last_seq", sequence_number)

# Alert decision worker distributed lock
redis.set("lock:alert_decision_worker", worker_instance_id, ex=30, nx=True)

# MQTT alert session control (written by alert decision worker)
redis.publish(f"mqtt:devices:{device_id}:control",
              json.dumps({"cmd": "alert_session_start"}))
```

### 3.4 Supabase / Postgres Role

Supabase is the persistent record store. It is only written to by Process 2 (alert decision worker) using `SUPABASE_SERVICE_ROLE_KEY`. It is read by Process 3 (API server) using `SUPABASE_ANON_KEY` with row-level security applied.

Supabase is not used for real-time pipeline state. That is Redis's responsibility.

---

## 4. Height Estimation Module

### 4.1 Role in the Decision Pipeline

Height estimation is a mandatory subsystem that operates as a **secondary verifier with conditional activation**. It fulfils three roles, in priority order:

**Role 1 — Pre-fusion hard exclusion.** When a high-confidence height estimate contradicts the target profile reference height by more than 25 cm, the track is excluded from fusion entirely. This fires before `FusionEngine.fuse()` is called.

**Role 2 — Fusion consistency gate.** When the height estimate is within the exclusion threshold but outside the tolerance band (10 cm), and confidence is ≥ 0.70, a 30% penalty is applied to the base fusion score. Height never boosts the fusion score.

**Role 3 — Re-ID height discriminator.** When the Re-ID agent evaluates a new track as a potential re-entry of a recently-dead track, height is used as an additional discriminator. A height delta greater than 15 cm between the dead track's last estimate and the new track's estimate disqualifies the re-entry match regardless of clothing similarity.

### 4.2 Dependency on Camera Calibration

Height estimation requires a valid camera calibration record for the device that sourced the frame. The calibration record is stored in the `camera_calibrations` table in Supabase and loaded at inference worker startup.

The inference worker will not start if no calibration record exists for the configured device ID, unless `--skip-height-calibration` is passed explicitly (permitted in development mode only; blocked in production by the CI pipeline).

```python
# camera_calibration_module/calibration.py

from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class CameraCalibration:
    camera_id: str
    mount_height_m: float       # Measured: vertical distance from lens to floor
    tilt_angle_deg: float       # Measured: degrees below horizontal
    focal_length_px: float      # From calibration procedure or camera spec
    sensor_height_px: int       # Frame height in pixels (480 for this system)
    calibrated: bool            # False = module must self-disable

    def pixel_height_to_meters(
        self,
        pixel_height: float,
        subject_distance_m: Optional[float] = None
    ) -> Optional[float]:
        if not self.calibrated or pixel_height <= 0:
            return None
        if subject_distance_m is None:
            subject_distance_m = self.mount_height_m / math.tan(
                math.radians(max(self.tilt_angle_deg, 1.0))
            )
        scale = subject_distance_m / self.focal_length_px
        return round(pixel_height * scale, 3)
```

### 4.3 Calibration Procedure

Calibration is performed once per physical camera installation and must be repeated if the camera is moved, the lens is adjusted, or calibration drift is detected (see Section 15.3).

**Step 1:** Place a calibration marker of known height (1.800 m) at the centre of the intended monitoring zone.

**Step 2:** Issue a `calibration_request` command to the device via MQTT. The device captures and transmits a frame tagged `trigger: calibration`.

**Step 3:** The Height Calibration Assistant Agent (see Section 10.5) processes the frame, detects the calibration marker using the pose model, measures its pixel height, and computes `focal_length_px` using the known physical height and the approximate subject distance derived from `mount_height_m` and `tilt_angle_deg`.

```python
focal_length_px = (marker_pixel_height * subject_distance_m) / marker_physical_height_m
```

**Step 4:** The computed calibration record is written to `camera_calibrations` in Supabase. The inference worker reloads calibration data without restart.

**Step 5:** The agent emits a calibration report: computed `focal_length_px`, estimated error margin (± cm at 3 m distance), and a pass/fail verdict. Pass requires error margin ≤ 8 cm at 3 m.

### 4.4 Behavior When Calibration Is Absent or Invalid

| Condition | System Behavior |
|---|---|
| `calibrated = False` | Height module returns `None`. Fusion skips all height logic. No penalty. No exclusion. |
| Calibration record missing for device_id | Inference worker refuses to start (production). Warning logged, height disabled (dev mode). |
| Calibration drift detected (Section 15.3) | Alert emitted to operations channel. Height module self-disables until recalibration confirmed. |
| Pose model confidence < 0.50 | Height estimate suppressed. Returns `None`. |
| Pose not detected (missing keypoints) | Height estimate suppressed. Returns `None`. |
| Subject partially occluded below waist | Detected via missing lower-body keypoints. Height estimate suppressed. Returns `None`. |
| Subject seated or crouching | Detected via keypoint geometry (hip-ankle ratio). Height estimate suppressed. Returns `None`. |

In all suppression cases, `height_consistent` is set to `True` and `height_penalty_applied` is set to `False`. The system never penalises a track for insufficient height data.

### 4.5 Interaction with Edge-Sourced Frames

ESP32-CAM frames arrive at 640×480. The height estimation model (YOLOv8-pose) runs on this resolution. The pixel height extracted from the pose model is the distance from the crown keypoint to the ankle keypoint in the 640×480 coordinate space. This is passed directly to `pixel_height_to_meters()` using the calibration for the source device.

Because frames are sparse (0.5–5 FPS), the height estimate for a given track is updated only when a new frame arrives containing that track. Between frames, the last valid height estimate is held. If no estimate has been produced for a track within 30 seconds, the stored estimate is cleared and the next evaluation starts from scratch.

### 4.6 Hard Exclusion vs Soft Penalty Rules

```python
# surveillance_backend_pipeline.py

HEIGHT_HARD_EXCLUSION_DELTA_M = 0.25   # > 25 cm → exclude from fusion entirely
HEIGHT_SOFT_PENALTY_DELTA_M   = 0.10   # > 10 cm AND conf >= 0.70 → 30% penalty
HEIGHT_PENALTY_CONFIDENCE     = 0.70   # Minimum confidence to apply soft penalty
HEIGHT_EXCLUSION_CONFIDENCE   = 0.75   # Minimum confidence to apply hard exclusion

def evaluate_height_gate(
    estimate_m: float | None,
    reference_m: float | None,
    confidence: float,
    calibrated: bool
) -> tuple[str, bool, bool]:
    """
    Returns (action, height_consistent, height_penalty_applied).
    action: "exclude" | "penalise" | "pass"
    """
    if not calibrated or estimate_m is None or reference_m is None:
        return "pass", True, False

    delta = abs(estimate_m - reference_m)

    if delta > HEIGHT_HARD_EXCLUSION_DELTA_M and confidence >= HEIGHT_EXCLUSION_CONFIDENCE:
        return "exclude", False, False

    if delta > HEIGHT_SOFT_PENALTY_DELTA_M and confidence >= HEIGHT_PENALTY_CONFIDENCE:
        return "penalise", False, True

    return "pass", True, False
```

### 4.7 Failure-Safe Fallback Logic

If the height estimation model (`yolov8n-pose.pt`) fails to load at startup, the inference worker logs a `CRITICAL` error and continues with height disabled (`calibrated=False` equivalent). The worker does not crash. A Prometheus metric `pipeline_height_module_active` is set to 0. An alert is sent to the operations channel. Face and clothing processing continue unaffected.

---

## 5. Target Profile System

### 5.1 Identity Schema

```python
# config/target_profile.py

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class TargetProfile:
    person_id:            str                   # UUID, primary key
    display_name:         str                   # Human-readable label
    reference_embeddings: list[np.ndarray]      # ≥1 InsightFace 512-d embedding
    reference_height_m:   Optional[float]       # None disables height gating
    height_tolerance_m:   float = 0.10          # Default ±10 cm
    clothing_hints:       list[str] = field(default_factory=list)  # e.g. ["navy", "grey"]
    enrolled_at:          str = ""              # ISO8601 timestamp
    enrolled_by:          str = ""              # Operator ID
    notes:                str = ""
    active:               bool = True
```

Profiles are stored in the `target_profiles` table in Supabase (see Section 11) and loaded into memory by the inference worker at startup. Profile changes are detected via a Supabase realtime subscription and reloaded without process restart.

### 5.2 Enrollment Workflow

Enrollment is performed through the operator API. The inference worker does not perform enrollment.

```
POST /api/admin/profiles
Authorization: Bearer <operator_jwt>
Content-Type: application/json

{
  "display_name": "Subject Alpha",
  "reference_height_m": 1.82,
  "height_tolerance_m": 0.10,
  "clothing_hints": ["grey hoodie", "dark jeans"],
  "notes": "Primary target for this deployment"
}
→ 201 Created { "person_id": "uuid-here" }

POST /api/admin/profiles/{person_id}/embeddings
Authorization: Bearer <operator_jwt>
Content-Type: multipart/form-data
Field: image — JPEG of subject's face

→ 200 OK { "embedding_id": "uuid-here", "embedding_norm": 0.9987 }
```

The embedding endpoint runs the submitted image through InsightFace, extracts the 512-d embedding, verifies the embedding norm is in the range [0.95, 1.05] (basic quality check), signs the embedding file, and stores it in the `face_embeddings` table with `pgvector`. A minimum of 2 reference embeddings per profile is required before the profile becomes `active`.

### 5.3 How ESP32 Input Maps to Profiles

When a frame arrives from an ESP32 device, the `device_id` is used to look up the device registry record (Section 11.5), which includes a `zone_id`. Zones map to a list of `person_id` values that are considered targets for that zone. The inference worker compares extracted face embeddings only against profiles in the active target list for the frame's zone.

This prevents unnecessary computation and cross-zone false matches.

---

## 6. End-to-End Pipeline

This section defines the system's runtime behaviour deterministically. Every conditional branch has an explicit outcome.

### Step 1 — Edge Capture Trigger

The ESP32-CAM detects motion via frame differencing at 80×60 resolution. If `motion_ratio ≥ 0.012`, the device captures a 640×480 JPEG. If the face detector is available and returns `face_confidence < 0.40`, the frame is discarded and the device returns to motion monitoring. If `face_confidence ≥ 0.40` or face detection is unavailable, proceed to Step 2.

If fewer than 500 ms have elapsed since the last transmitted frame, the frame is discarded. Proceed to Step 2 only when the rate limit allows.

### Step 2 — Secure Transmission

The device computes `device_hmac = HMAC-SHA256(jpeg_bytes, device_secret)`. It assembles the multipart payload and POSTs to `/api/ingest/frame` with its device JWT in the Authorization header. If the POST succeeds (202), the device stores the `sequence_number` as the last acknowledged sequence. If the POST fails, the frame is queued per Section 2.5.2.

### Step 3 — Backend Ingestion and Validation

The ingestion endpoint (Process 3) validates the device JWT, verifies the HMAC, checks the sequence number for replay, and writes the frame to Redis stream `stream:frames:incoming`. It returns 202. The inference worker is the sole consumer of this stream.

### Step 4 — Inference Worker: Frame Receipt

The inference worker reads from `stream:frames:incoming` using `XREADGROUP`. It decodes the base64 JPEG to a NumPy array. It reads the source `device_id` from the metadata and loads the corresponding `CameraCalibration` record from its in-memory cache.

### Step 5 — Motion Gate Check

The inference worker runs its own `MotionGate` on the received frame. Because ESP32 already filters for motion, this will rarely skip frames. It exists to handle the case where the edge device's motion threshold differs from the backend's expectation, and to populate the `pipeline_frames_skipped_motion_total` Prometheus metric accurately. If the motion gate returns `False`, the tracker receives a null detection update (to maintain track state), and Steps 6–14 are skipped for this frame.

### Step 6 — YOLO Detection and DeepSORT Tracking

YOLOv8 runs person detection on the 640×480 frame. Detected person bounding boxes are passed to DeepSORT. DeepSORT outputs a list of confirmed tracks with IDs, centroids, and bounding boxes. Tracks that transitioned from `confirmed` to `lost` in this frame are passed to `FaceExtractorNode.on_tracks_lost()` and `ReIDAgent.on_track_lost()` immediately.

### Step 7 — Re-ID Agent: New Track Evaluation

For each newly confirmed track (track ID not seen in the previous frame), `ReIDAgent.on_track_confirmed()` is called with the track's centroid and clothing histogram. If the agent returns a `verified_identity`, this identity is passed as prior context to the explainability engine and the face cache lookup is bypassed in favour of a fresh face comparison. If no inherited identity is returned, normal processing continues.

### Step 8 — Parallel Feature Extraction

For each confirmed track, three extraction operations run:

**8a — Face extraction.** `FaceExtractorNode` checks the TTL cache for `track_id`. Cache entries expire after 30 seconds. If no valid cache entry exists, InsightFace runs on the face crop. If a face is detected, a 512-d embedding is extracted. The result is compared against all active target profiles for this zone using cosine similarity. `face_score = max cosine similarity across all reference embeddings for matching profile`. If no face is detected, `face_score = 0.0`.

**8b — Clothing extraction.** An HSV histogram is computed on the person bounding box crop. The dominant colour bin is identified. `clothing_score` is the cosine similarity between the current histogram and the target profile's clothing hint histograms (if defined), otherwise it is a normalised descriptor score derived from histogram entropy. Range: [0.0, 1.0].

**8c — Height estimation.** YOLOv8-pose runs on the full frame (not the crop). Crown and ankle keypoints are extracted for the track's bounding box region. `pose_confidence` is the minimum keypoint confidence for the crown-to-ankle pair. If `pose_confidence < 0.50` or lower-body keypoints are absent, height estimation returns `None`. Otherwise, `pixel_height` is computed as the crown-to-ankle keypoint distance in pixels and converted to meters via `calibration.pixel_height_to_meters()`.

### Step 9 — Pre-Fusion Height Hard Exclusion

`evaluate_height_gate()` is called with the height estimate, the target profile's `reference_height_m`, `pose_confidence`, and `calibration.calibrated`. If the result is `"exclude"`, this track is logged as height-excluded, no fusion is performed, no alert candidate is generated, and the pipeline continues to the next track.

### Step 10 — Fusion Engine

`FusionEngine.fuse()` is called with `face_score`, `clothing_score`, and height data. See Section 7 for the exact scoring model.

### Step 11 — Alert Candidate Emission

If `fusion_score ≥ CANDIDATE_THRESHOLD` (default 0.45), the track's fusion output is written to Redis stream `stream:alert_candidates`. The inference worker also publishes the current pipeline state to Redis key `pipeline:state`.

### Step 12 — Temporal Validation (Process 2)

The alert decision worker reads from `stream:alert_candidates`. The `TemporalValidator` checks whether the track has produced a fusion score above `CANDIDATE_THRESHOLD` in at least `TEMPORAL_MIN_FRAMES` (default 3) of the last `TEMPORAL_WINDOW_FRAMES` (default 10) frames. If not, the candidate is acknowledged in the Redis stream and discarded.

### Step 13 — Behavioural Anomaly Scoring

The `BehavioralAnomalyAgent` evaluates the track's dwell time, region revisits, and velocity variance. If `escalate_priority = True` and the current candidate priority would be `low` or `medium`, priority is escalated to `high`.

### Step 14 — Explainability, Audit, and Alert Write

The explainability engine constructs a structured `AlertExplanation` dict. The audit log appends the alert payload to the hash chain and returns the `payload_hash`. The complete alert record (including `payload_hash`) is written to Supabase `alerts` table. The alert decision worker publishes an MQTT alert session start command to the source device if the alert level is `confirmed`.

---

## 7. Fusion Engine

### 7.1 Exact Scoring Model

```python
# multi_attribute_fusion_module/fuser.py

from dataclasses import dataclass

FACE_WEIGHT     = 0.65
CLOTHING_WEIGHT = 0.35
HEIGHT_PENALTY_FACTOR = 0.70   # Applied when height contradiction confirmed

@dataclass
class FusionInput:
    face_score:             float          # [0.0, 1.0]; 0.0 if no face detected
    clothing_score:         float          # [0.0, 1.0]
    height_consistent:      bool           # From evaluate_height_gate()
    height_penalty_applied: bool           # From evaluate_height_gate()

@dataclass
class FusionOutput:
    fusion_score:           float          # Final score [0.0, 1.0]
    alert_level:            str            # "confirmed" | "candidate" | "suppressed"
    priority:               str            # "high" | "medium" | "low"
    height_consistent:      bool
    height_penalty_applied: bool
    signal_breakdown:       dict

def fuse(self, inputs: FusionInput) -> FusionOutput:
    # Base score: face-dominant when face is available
    if inputs.face_score > 0.0:
        base_score = (FACE_WEIGHT * inputs.face_score +
                      CLOTHING_WEIGHT * inputs.clothing_score)
    else:
        # Clothing-only mode: full weight on clothing
        base_score = inputs.clothing_score

    # Height penalty: only reduces, never increases
    if inputs.height_penalty_applied:
        final_score = base_score * HEIGHT_PENALTY_FACTOR
    else:
        final_score = base_score

    final_score = round(min(final_score, 1.0), 4)

    # Alert level determination
    if final_score >= 0.72:
        alert_level = "confirmed"
    elif final_score >= 0.45:
        alert_level = "candidate"
    else:
        alert_level = "suppressed"

    # Priority determination
    if final_score >= 0.85:
        priority = "high"
    elif final_score >= 0.65:
        priority = "medium"
    else:
        priority = "low"

    return FusionOutput(
        fusion_score=final_score,
        alert_level=alert_level,
        priority=priority,
        height_consistent=inputs.height_consistent,
        height_penalty_applied=inputs.height_penalty_applied,
        signal_breakdown={
            "face_score": round(inputs.face_score, 4),
            "clothing_score": round(inputs.clothing_score, 4),
            "base_score": round(base_score, 4),
            "height_penalty": inputs.height_penalty_applied,
            "final_score": final_score
        }
    )
```

### 7.2 Threshold Rules

| Threshold | Value | Effect |
|---|---|---|
| `CANDIDATE_THRESHOLD` | 0.45 | Minimum score to emit alert candidate to Redis |
| `CONFIRMED_THRESHOLD` | 0.72 | Alert level = "confirmed" |
| `HIGH_PRIORITY_THRESHOLD` | 0.85 | Priority = "high" |
| `MEDIUM_PRIORITY_THRESHOLD` | 0.65 | Priority = "medium" |
| `HEIGHT_EXCLUSION_DELTA_M` | 0.25 m | Hard exclusion (pre-fusion) |
| `HEIGHT_PENALTY_DELTA_M` | 0.10 m | Soft penalty trigger |
| `HEIGHT_PENALTY_CONFIDENCE` | 0.70 | Minimum confidence for soft penalty |
| `HEIGHT_EXCLUSION_CONFIDENCE` | 0.75 | Minimum confidence for hard exclusion |
| `TEMPORAL_MIN_FRAMES` | 3 | Frames above threshold in window to confirm |
| `TEMPORAL_WINDOW_FRAMES` | 10 | Rolling window size for temporal validation |

### 7.3 Contradiction Handling

**Face vs clothing contradiction:** No special handling. Both signals contribute per weight. A low clothing score with a high face score still produces a confirmed alert if the face score is strong enough (0.72 / 0.65 = 1.11, so face_score ≥ 1.11 is impossible; in practice face ≥ 0.90 produces 0.65×0.90 + 0.35×0.0 = 0.585 confirmed at candidate level only). A face_score ≥ 0.96 is required for a confirmed alert in clothing-absent mode, which is intentionally conservative.

**Height vs face contradiction:** If height hard-excludes the track, no alert is generated regardless of face score. This is the only signal that can veto a face match.

**Temporal contradiction:** A track that reaches `confirmed` alert level on one frame but then drops below `CANDIDATE_THRESHOLD` for the next 9 frames will not generate an alert. Temporal validation requires sustained evidence.

---

## 8. Tracking and Re-Identification

### 8.1 Track Lifecycle

```
[new_detection] → TENTATIVE (1-3 frames) → CONFIRMED → LOST → DELETED
                                               ↑           |
                                     re-confirmed if      30s window
                                     re-detected           for Re-ID
```

**TENTATIVE:** DeepSORT requires 3 consecutive detections before confirming a track. No feature extraction occurs on tentative tracks.

**CONFIRMED:** Full feature extraction pipeline runs. Alert candidates may be emitted.

**LOST:** No detection for 1 consecutive frame. Track is held in memory. Feature extraction pauses.

**DELETED:** No detection for `MAX_AGE` frames (default 30 at 2 FPS effective rate = 15 seconds). Track is deleted. `on_tracks_lost()` is called. Re-ID window opens for 30 seconds.

### 8.2 ESP32-Induced Frame Sparsity Handling

Because the ESP32 transmits at 0.5–5 FPS (not 30 FPS), DeepSORT's motion model requires adjustment. The Kalman filter's process noise (`Q`) and measurement noise (`R`) matrices must be scaled for the actual frame interval.

```python
# multi_object_tracking_module/config.py

DEFAULT_BACKEND = "deepsort"            # Canonical default — never bytetrack in production

DEEPSORT_MAX_AGE = 30                   # Frames before track deletion
DEEPSORT_N_INIT = 3                     # Frames to confirm a track
DEEPSORT_MAX_IOU_DISTANCE = 0.7
DEEPSORT_MAX_COSINE_DISTANCE = 0.4

# Frame interval scaling for sparse input
# At 2 FPS, inter-frame interval = 500ms. DeepSORT assumes ~33ms.
# Scale process noise by actual_interval / assumed_interval
DEEPSORT_FRAME_INTERVAL_MS = 500        # Updated dynamically from frame metadata timestamps
DEEPSORT_ASSUMED_INTERVAL_MS = 33
DEEPSORT_NOISE_SCALE = DEEPSORT_FRAME_INTERVAL_MS / DEEPSORT_ASSUMED_INTERVAL_MS
```

The inference worker computes the actual inter-frame interval from consecutive `received_at` timestamps in the frame metadata and updates `DEEPSORT_NOISE_SCALE` dynamically. This prevents the Kalman filter from over-predicting position drift between sparse frames.

### 8.3 Track ID Stability Across Intermittent Input

Because frames arrive intermittently, a person may leave the frame for several seconds (walking behind an obstacle, frame rate gap) and re-enter. The Re-ID agent handles this case.

```python
# re_identification_module/reid_agent.py

REID_WINDOW_SECONDS    = 30.0   # Dead track descriptor retained for 30s
REID_COLOR_THRESHOLD   = 0.82   # Clothing histogram cosine similarity
REID_SPATIAL_THRESHOLD = 200    # Max pixel distance (at 640×480)
REID_HEIGHT_DELTA_M    = 0.15   # Height delta above which re-entry is rejected

@dataclass
class TrackDescriptor:
    track_id:           int
    last_centroid:      tuple[float, float]
    clothing_color:     str
    clothing_histogram: np.ndarray | None
    height_estimate_m:  float | None
    height_confidence:  float
    died_at:            float
    verified_identity:  str | None
```

When a new track is confirmed, `ReIDAgent.on_track_confirmed()` compares against all dead track descriptors within the re-ID window. A re-entry match requires:
- Spatial distance ≤ `REID_SPATIAL_THRESHOLD`
- Clothing similarity ≥ `REID_COLOR_THRESHOLD`
- Height delta ≤ `REID_HEIGHT_DELTA_M` (if both estimates are available)

If all three conditions are met, the verified identity from the dead track is inherited and a fresh face comparison is requested.

---

## 9. Security Architecture

### 9.1 JWT Authentication

Two separate JWT signing keys are used: one for operator/dashboard users (`JWT_SECRET_KEY`) and one for ESP32 devices (`DEVICE_JWT_SECRET`). These keys must never be the same value.

**Operator JWT:** 15-minute expiry. Issued by `/api/auth/login` after credential validation. Required on all `/api/state`, `/api/alerts`, `/api/frame.jpg`, `/api/admin/*` endpoints.

**Device JWT:** 24-hour expiry. Issued once during device provisioning via `/api/admin/devices/provision`. Stored in device firmware flash. Required on `/api/ingest/frame`. Contains claims: `device_id`, `zone_id`, `firmware_version`.

### 9.2 ESP32 Device Authentication

Device identity is verified in two independent layers:

**Layer 1 — Device JWT.** Proves the device was provisioned by an operator. Validated on every ingest request.

**Layer 2 — Frame HMAC.** Proves the frame bytes were produced by the specific device (not replayed or injected). `HMAC-SHA256(frame_bytes, device_secret)` is recomputed server-side using `device_secret` stored in the `device_registry` table. A mismatch returns 403.

**Replay prevention.** The `sequence_number` field in frame metadata must strictly increase. The last accepted sequence number is stored in Redis per device. Out-of-order or duplicate sequence numbers return 409.

### 9.3 Signed Embedding Store

Reference face embeddings are stored as `.npz` files with a companion `.sig` file containing `HMAC-SHA256(file_bytes, EMBEDDING_SIGNING_KEY)`.

```python
# facial_recognition_module/src/embedding_store.py

def load_embeddings(path: Path) -> dict:
    sig_path = path.with_suffix(".sig")
    if not sig_path.exists():
        raise RuntimeError(f"[SECURITY] Signature missing: {sig_path}")
    if not hmac.compare_digest(sig_path.read_text().strip(), _sign_file(path)):
        raise RuntimeError("[SECURITY] Embedding file tampered. Pipeline will not start.")
    return dict(np.load(path))
```

Startup fails hard if embedding integrity cannot be confirmed. There is no fallback to unsigned embeddings.

### 9.4 Supabase Row-Level Security

```sql
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Process 2 only: insert
CREATE POLICY "backend_insert_only" ON alerts FOR INSERT
  TO service_role WITH CHECK (true);

-- Dashboard: read non-suppressed alerts
CREATE POLICY "dashboard_read" ON alerts FOR SELECT
  TO anon USING (status != 'suppressed');

-- No UPDATE, no DELETE via API. Mutations only via service_role
-- in controlled alert lifecycle transitions.
```

### 9.5 Alert Crop Encryption

Person crops saved to `runtime/artifacts/alerts/` are encrypted with Fernet using `CROP_ENCRYPTION_KEY`. Plaintext crops are never written to disk. The API server decrypts on-the-fly per authenticated request and streams JPEG bytes directly without caching the decrypted file.

### 9.6 TLS Requirements

- Backend API server: TLS 1.2 minimum, TLS 1.3 preferred. Certificate from a public CA.
- MQTT broker: TLS 1.2 minimum on port 8883.
- ESP32 firmware: certificate pinning using the backend certificate's SHA-256 fingerprint, compiled into firmware at build time.
- Supabase connection: TLS enforced by Supabase. `sslmode=require` in all connection strings.

### 9.7 Secret Management

No secrets are stored in `.env` files in production. All secrets are injected as environment variables from the cloud secret manager (AWS Secrets Manager or equivalent).

| Secret Name | Used By | Description |
|---|---|---|
| `JWT_SECRET_KEY` | Process 3 | Operator JWT signing key |
| `DEVICE_JWT_SECRET` | Process 3 | Device JWT signing key |
| `EMBEDDING_SIGNING_KEY` | Process 1 | HMAC key for embedding integrity |
| `CROP_ENCRYPTION_KEY` | Process 2, 3 | Fernet key for crop encryption |
| `SUPABASE_URL` | Process 2, 3 | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Process 2 | Privileged write key |
| `SUPABASE_ANON_KEY` | Process 3 | Read-only dashboard key |
| `DATABASE_URL` | Process 2, CI | Direct Postgres connection |
| `MQTT_BROKER_PASSWORD` | Mosquitto | Broker admin password |
| `MODELS_S3_BUCKET` | CI, Dockerfile | Model weight artifact store |
| `CALIBRATION_AGENT_API_KEY` | Agent | Anthropic API key for calibration agent |

---

## 10. AI Agents

### 10.1 Track Continuity Resolver

**Where it runs:** Inline within the inference worker (Process 1), called during the Re-ID evaluation step.  
**Data consumed:** Dead track descriptor (clothing histogram, height estimate, last centroid), new track descriptor.  
**System decision affected:** Whether to inherit a verified identity from a dead track, bypassing the face cache and requesting a fresh face comparison.  
**Implementation:** Rule-based agent within `ReIDAgent` (Section 8.3). Uses spatial proximity, clothing histogram cosine similarity, and height delta thresholds. No LLM call required for real-time operation.  
**LLM enhancement (expo mode):** When a re-entry match is confirmed, an optional Anthropic API call generates a human-readable re-identification narrative for the dashboard: "Track 7 re-identified as Subject Alpha after 8-second gap. Match confidence: clothing 0.91, height consistent. Fresh face comparison requested."

### 10.2 Anomalous Behavior Detector

**Where it runs:** Process 2 (alert decision worker), post-fusion, pre-alert-write.  
**Data consumed:** `TrackBehavior` struct — centroid history, region visit counts, dwell time, velocity variance.  
**System decision affected:** Alert priority escalation. If `escalate_priority = True` and current priority is `low` or `medium`, priority is escalated to `high`. Behavioural flags are written to the `explanation` JSONB field.

```python
# behavioral_anomaly_module/anomaly_agent.py

class BehavioralAnomalyAgent:
    LOITER_THRESHOLD_SECONDS  = 120
    REVISIT_THRESHOLD         = 3
    LOW_VELOCITY_VAR_THRESHOLD = 5.0

    def score(self, behavior: TrackBehavior) -> dict:
        flags = []
        if behavior.dwell_seconds >= self.LOITER_THRESHOLD_SECONDS:
            flags.append("loitering")
        if behavior.max_region_revisits() >= self.REVISIT_THRESHOLD:
            flags.append("repeated_revisit")
        if (behavior.velocity_variance < self.LOW_VELOCITY_VAR_THRESHOLD
                and behavior.dwell_seconds > 30):
            flags.append("stationary")
        return {
            "behavioral_flags": flags,
            "escalate_priority": len(flags) >= 2
        }
```

Region of interest polygons are defined in `config/regions_of_interest.json` as named pixel-coordinate polygon arrays, loaded at worker startup.

### 10.3 Alert Integrity Monitor

**Where it runs:** Scheduled nightly cron job (separate process, minimal footprint).  
**Data consumed:** `runtime/audit/alert_chain.jsonl`.  
**System decision affected:** Emits a `CRITICAL` log and sets Prometheus metric `pipeline_audit_chain_intact = 0` if chain verification fails. Pages operations.  
**Implementation:**

```python
def nightly_integrity_check():
    log = AlertAuditLog(Path("runtime/audit/alert_chain.jsonl"))
    intact = log.verify_chain()
    prometheus_gauge("pipeline_audit_chain_intact").set(1 if intact else 0)
    if not intact:
        send_operations_alert("CRITICAL: Alert audit chain integrity failure.")
```

### 10.4 Adaptive Inference Scheduler

**Where it runs:** Inference worker (Process 1), first operation in the frame loop.  
**Data consumed:** Current frame (grayscale downsampled), prior frame.  
**System decision affected:** Whether to run full inference pipeline on the current frame. When `MotionGate.should_process()` returns `False`, the tracker receives a null update and all downstream processing is skipped.

```python
class MotionGate:
    def __init__(self, threshold: float = 0.005):
        self._prev_gray = None
        self._threshold = threshold

    def should_process(self, frame: np.ndarray) -> bool:
        gray = cv2.GaussianBlur(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0
        )
        if self._prev_gray is None:
            self._prev_gray = gray
            return True
        diff = cv2.absdiff(self._prev_gray, gray)
        motion_ratio = np.count_nonzero(diff > 25) / diff.size
        self._prev_gray = gray
        return motion_ratio >= self._threshold
```

Note: Because the ESP32 already performs edge-level motion filtering, this gate primarily prevents stale cached frames (from network jitter redelivery) from triggering full inference. The skip ratio metric (`pipeline_frames_skipped_motion_total`) is expected to be low in normal operation.

### 10.5 Height Calibration Assistant Agent

**Where it runs:** Standalone process, invoked by operator via API. Makes calls to the Anthropic API (claude-sonnet-4-20250514).  
**Data consumed:** Calibration frame from ESP32 (triggered via MQTT `calibration_request`), known marker height (1.800 m), camera mount parameters (`mount_height_m`, `tilt_angle_deg`).  
**System decision affected:** Writes a validated `CameraCalibration` record to Supabase. Enables height estimation for the device. Reloads inference worker calibration cache.

**Agent workflow:**

```python
async def run_calibration_agent(
    frame_bytes: bytes,
    device_id: str,
    mount_height_m: float,
    tilt_angle_deg: float
) -> CalibrationResult:

    # Step 1: Run YOLOv8-pose on calibration frame to detect marker keypoints
    marker_pixel_height = extract_marker_pixel_height(frame_bytes)

    # Step 2: Compute focal length
    import math
    subject_distance_m = mount_height_m / math.tan(math.radians(tilt_angle_deg))
    focal_length_px = (marker_pixel_height * subject_distance_m) / 1.800

    # Step 3: Compute error margin at 3m reference distance
    test_height = CameraCalibration(
        camera_id=device_id,
        mount_height_m=mount_height_m,
        tilt_angle_deg=tilt_angle_deg,
        focal_length_px=focal_length_px,
        sensor_height_px=480,
        calibrated=True
    ).pixel_height_to_meters(marker_pixel_height, subject_distance_m)
    error_m = abs(test_height - 1.800)

    # Step 4: LLM-generated calibration report
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"Camera calibration result for device {device_id}:\n"
                f"Computed focal_length_px: {focal_length_px:.1f}\n"
                f"Estimated error at 3m: {error_m*100:.1f} cm\n"
                f"Pass threshold: 8 cm\n"
                f"Write a 2-sentence operator-facing calibration report. "
                f"State pass or fail and what the operator should do next."
            )
        }]
    )
    report = response.content[0].text

    passed = error_m <= 0.08
    if passed:
        # Write calibration to Supabase
        write_calibration_record(device_id, focal_length_px, mount_height_m, tilt_angle_deg)

    return CalibrationResult(
        passed=passed,
        focal_length_px=focal_length_px,
        error_m=error_m,
        report=report
    )
```

---

## 11. Data Models

### 11.1 Alerts Table

```sql
CREATE TABLE IF NOT EXISTS alerts (
    alert_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id            INTEGER NOT NULL,
    camera_id           TEXT NOT NULL DEFAULT 'default',
    device_id           TEXT NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    face_score          NUMERIC(5,4),
    clothing_color      TEXT,
    clothing_score      NUMERIC(5,4),
    height_m            NUMERIC(5,3),
    height_consistent   BOOLEAN DEFAULT FALSE,
    height_calibrated   BOOLEAN NOT NULL DEFAULT FALSE,
    fusion_score        NUMERIC(5,4) NOT NULL,
    temporal_valid      BOOLEAN NOT NULL DEFAULT FALSE,
    priority            TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    status              TEXT NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new','acknowledged','resolved','false_positive')),
    alert_level         TEXT NOT NULL
                            CHECK (alert_level IN ('confirmed','candidate','suppressed')),
    explanation         JSONB NOT NULL DEFAULT '{}',
    behavioral_flags    TEXT[] NOT NULL DEFAULT '{}',
    crop_path           TEXT,
    payload_hash        TEXT NOT NULL,
    person_id           UUID REFERENCES target_profiles(person_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_timestamp  ON alerts (timestamp DESC);
CREATE INDEX idx_alerts_track_id   ON alerts (track_id);
CREATE INDEX idx_alerts_status     ON alerts (status);
CREATE INDEX idx_alerts_priority   ON alerts (priority);
CREATE INDEX idx_alerts_person_id  ON alerts (person_id);
CREATE INDEX idx_alerts_device_id  ON alerts (device_id);
```

### 11.2 Face Embeddings (pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS face_embeddings (
    embedding_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID NOT NULL REFERENCES target_profiles(person_id),
    embedding       VECTOR(512) NOT NULL,
    embedding_norm  NUMERIC(6,4) NOT NULL,
    source_image    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_person ON face_embeddings (person_id);
CREATE INDEX idx_embeddings_vector ON face_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
```

### 11.3 Camera Calibrations

```sql
CREATE TABLE IF NOT EXISTS camera_calibrations (
    camera_id           TEXT PRIMARY KEY,
    device_id           TEXT NOT NULL REFERENCES device_registry(device_id),
    mount_height_m      NUMERIC(5,3) NOT NULL,
    tilt_angle_deg      NUMERIC(5,2) NOT NULL,
    focal_length_px     NUMERIC(8,2) NOT NULL,
    sensor_height_px    INTEGER NOT NULL DEFAULT 480,
    calibrated          BOOLEAN NOT NULL DEFAULT TRUE,
    error_margin_m      NUMERIC(5,3),
    calibrated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    calibrated_by       TEXT NOT NULL,
    invalidated_at      TIMESTAMPTZ,
    invalidation_reason TEXT
);
```

### 11.4 Target Profiles

```sql
CREATE TABLE IF NOT EXISTS target_profiles (
    person_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name        TEXT NOT NULL,
    reference_height_m  NUMERIC(5,3),
    height_tolerance_m  NUMERIC(4,3) NOT NULL DEFAULT 0.10,
    clothing_hints      TEXT[] DEFAULT '{}',
    enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    enrolled_by         TEXT NOT NULL,
    notes               TEXT DEFAULT '',
    active              BOOLEAN NOT NULL DEFAULT FALSE,
    min_embeddings_met  BOOLEAN NOT NULL DEFAULT FALSE
);
```

### 11.5 Device Registry

```sql
CREATE TABLE IF NOT EXISTS device_registry (
    device_id           TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    zone_id             TEXT NOT NULL,
    device_secret_hash  TEXT NOT NULL,  -- bcrypt hash of device_secret
    firmware_version    TEXT NOT NULL DEFAULT '3.0.0',
    last_seen_at        TIMESTAMPTZ,
    last_seq_number     BIGINT NOT NULL DEFAULT 0,
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    provisioned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provisioned_by      TEXT NOT NULL
);
```

### 11.6 Explanation JSON Schema

The `explanation` JSONB field in `alerts` must always conform to:

```json
{
  "primary_signal": "face | clothing | face+clothing",
  "face": {
    "score": 0.0,
    "quality": "strong | moderate | weak | null"
  },
  "clothing": {
    "color": "navy",
    "score": 0.0
  },
  "height": {
    "estimate_m": 1.82,
    "consistent": true,
    "penalty_applied": false,
    "calibrated": true,
    "confidence": 0.81
  },
  "temporal": {
    "frames_validated": 5,
    "stability_score": 0.78
  },
  "fusion_score": 0.74,
  "behavioral_flags": [],
  "priority": "high",
  "confidence": 0.74
}
```

---

## 12. Failure Handling

### 12.1 ESP32 Offline

**Detection:** Redis key `device:{device_id}:last_seen` has a 10-second TTL, refreshed on each successful frame ingest. If the key expires, the device is considered offline.

**Effect on pipeline:** Inference worker continues processing any queued frames. If no frames arrive for 30 seconds, active tracks begin aging toward `LOST` state. After `MAX_AGE` frames worth of elapsed time with no new input, tracks are deleted. No false alerts are generated from stale track state.

**Recovery:** When the device reconnects, it transmits queued frames (up to 8). The inference worker processes them sequentially. Track IDs from before the disconnection are eligible for Re-ID matching if within the 30-second Re-ID window.

**Operator notification:** A Prometheus alert fires when `device:{device_id}:last_seen` expires. The dashboard shows device offline status.

### 12.2 Packet Loss and Delayed Frames

Delayed frames (arriving out of sequence) are detected by the sequence number check at ingestion. Frames arriving more than 60 seconds late (detected by comparing `metadata.timestamp_ms` against `received_at`) are processed but flagged with `late_frame: true` in their metadata. Late frames do not reset the Track `MAX_AGE` timer. Height estimates from late frames are accepted if within the 30-second TTL window.

### 12.3 Backend Overload

The Redis stream `stream:frames:incoming` acts as the buffer. If the inference worker falls behind, frames queue in Redis up to `MAXLEN 500`. Frames beyond this limit are dropped (oldest first). The inference worker publishes a `pipeline_queue_depth` Prometheus metric. If queue depth exceeds 100, a warning is emitted. If it exceeds 400, a critical alert is emitted.

If the inference worker crashes, the Redis stream retains all unprocessed frames. On restart, the worker resumes from its last consumer group position and processes the backlog.

### 12.4 Calibration Drift

Calibration drift is detected by the nightly `calibration_health_check` job. It compares the current `focal_length_px` against an expected range derived from a reference fixture in the camera's field of view (a permanent marker installed at known position during camera installation). If the measured `focal_length_px` deviates more than 5% from the stored calibration value, drift is declared.

On drift detection: the `camera_calibrations` record is updated with `invalidated_at = NOW()` and `invalidation_reason = "drift_detected"`. The inference worker detects this via its Supabase realtime subscription and disables height estimation for the affected device. An operations alert is emitted with the measured drift magnitude.

### 12.5 GPU Failure

If the YOLO or InsightFace model raises a CUDA exception, the inference worker catches it and logs `CRITICAL`. If the error is transient (OOM on a single frame), the frame is discarded and processing continues. If the error recurs on 5 consecutive frames, the worker assumes a GPU fault and exits with code 1. Kubernetes restarts it with exponential backoff.

### 12.6 Supabase Unavailability

Alert candidates continue to accumulate in the Redis stream. The alert decision worker retries Supabase writes with exponential backoff (1s, 2s, 4s, 8s, max 60s). Simultaneously, all alert payloads are written to the local audit chain. On Supabase recovery, the worker drains the backlog. Redis stream `MAXLEN` for `stream:alert_candidates` is set to 10,000 to bound memory use during extended outages.

### 12.7 Alert Decision Worker Crash

Because alert candidates are stored in a Redis stream with consumer group acknowledgement, no candidates are lost. On restart, the worker acquires the distributed lock, re-initialises `TemporalValidator` state (initially empty — this means the first few alerts after restart require re-establishing temporal history), and resumes reading from the last unacknowledged stream position.

---

## 13. Deployment Architecture

### 13.1 Edge Firmware

**Build tool:** PlatformIO  
**Target:** ESP32-CAM (AI-Thinker)  
**Framework:** Arduino (ESP-IDF compatible)  
**Libraries:** ESP-WHO (face detection), ArduinoJson, PubSubClient (MQTT), esp32cam  
**Firmware CI:** GitHub Actions — compile-check on every push. Release tags trigger a build artifact upload to S3.

**Device provisioning flow:**
1. Operator calls `POST /api/admin/devices/provision` with `display_name`, `zone_id`.
2. Backend generates `device_id`, `device_secret`, and a device JWT.
3. Operator flashes firmware with embedded `device_id`, `device_secret`, backend URL, and certificate fingerprint.
4. Device powers on, registers with backend, and is marked `active` in the device registry.

### 13.2 Backend Containerisation

```dockerfile
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 curl awscli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN bash scripts/fetch_models.sh || echo "[WARN] Model fetch deferred to runtime"
RUN python -c "import insightface; a = insightface.app.FaceAnalysis('buffalo_l'); a.prepare(ctx_id=-1)" || true

EXPOSE 3000 9090 8883
```

**Three services in `docker-compose.yml`:**

```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    ports: ["8883:8883"]
    volumes:
      - ./config/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./certs:/mosquitto/certs:ro

  inference:
    build: .
    command: python inference_worker.py --backend deepsort
    restart: unless-stopped
    depends_on: [redis]
    env_file: .env.production
    volumes:
      - ./runtime:/app/runtime
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  alert-worker:
    build: .
    command: python alert_decision_worker.py
    restart: unless-stopped
    depends_on: [redis]
    env_file: .env.production
    volumes:
      - ./runtime:/app/runtime

  api:
    build: .
    restart: unless-stopped
    depends_on: [redis, mosquitto]
    env_file: .env.production
    ports: ["3000:3000", "9090:9090"]
    volumes:
      - ./runtime/artifacts:/app/runtime/artifacts:ro
```

### 13.3 Scaling Model

| Component | Scale strategy |
|---|---|
| ESP32-CAM | One device per monitored zone. Add devices per zone. |
| Inference worker | Single instance. Scale vertically (more GPU). |
| Alert decision worker | Single instance. Redis stream buffers load spikes. |
| API server | Horizontal — add replicas behind load balancer. |
| Redis | Single instance for this deployment. Redis Sentinel for HA. |
| Supabase | Managed. Connection pool via PgBouncer. |

### 13.4 Model Distribution

All `.pt` files are excluded from the git repository. Models are fetched and checksum-verified at container build time by `scripts/fetch_models.sh` from the S3 bucket defined by `MODELS_S3_BUCKET`.

| Model | Used by | Checksum (SHA-256) |
|---|---|---|
| `yolov8n.pt` | Person detection | Defined in `scripts/fetch_models.sh` |
| `yolov8s.pt` | DeepSORT re-ID | Defined in `scripts/fetch_models.sh` |
| `yolov8n-pose.pt` | Height estimation | Defined in `scripts/fetch_models.sh` |
| `buffalo_l` (InsightFace) | Face recognition | Pre-downloaded in Dockerfile |

---

## 14. Performance Constraints

### 14.1 End-to-End Latency Budget

| Stage | Maximum latency |
|---|---|
| ESP32 capture → HTTPS POST complete | 800 ms |
| Backend ingestion → Redis enqueue | 50 ms |
| Redis enqueue → Inference worker frame read | 100 ms |
| YOLO + DeepSORT per frame | 150 ms (GPU) |
| Face + clothing + height extraction | 200 ms (GPU) |
| Fusion + Redis alert candidate write | 20 ms |
| Temporal validation + alert decision | 100 ms (CPU) |
| Supabase alert write | 150 ms |
| **Total: ESP32 capture → alert in Supabase** | **< 2 seconds** |

Dashboard polling latency (Redis pipeline state): < 2 seconds (TTL-bound).

### 14.2 Bandwidth Assumptions

| Scenario | Transmission rate | Bandwidth required |
|---|---|---|
| Idle (no motion) | 0 FPS | 0 |
| Normal monitoring | 0.5–2 FPS | 50–200 KB/s |
| Alert session | 5 FPS | 250 KB/s |
| Backend → Supabase | Per alert | < 5 KB per alert record |

Minimum uplink bandwidth at ESP32 installation site: 2 Mbps for alert session support.

### 14.3 FPS Under Constrained Input

The backend inference worker is designed for sparse input. At 2 FPS input, the worker operates at approximately 10–15% GPU utilisation (GPU-bound models run faster than the input rate). At 5 FPS (alert session), GPU utilisation rises to approximately 35–50%.

The system makes no guarantee about real-time processing of continuous 30 FPS video. If a webcam override is used in development mode (`--dev-mode`), the motion gate reduces effective processing rate to approximately 5–10 FPS depending on scene dynamics.

### 14.4 Height Estimation Overhead

YOLOv8-pose adds approximately 40–60 ms per frame on a mid-range GPU (RTX 3060 equivalent). On frames where no valid pose is detected, the overhead drops to approximately 15 ms (model forward pass without post-processing). This overhead is acceptable within the 2-second end-to-end latency budget.

---

## 15. Monitoring and Observability

### 15.1 Prometheus Metrics

```python
# metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Inference worker
frames_received          = Counter("pipeline_frames_received_total", "Frames received from ESP32", ["device_id"])
frames_processed         = Counter("pipeline_frames_processed_total", "Frames processed by inference")
frames_skipped_motion    = Counter("pipeline_frames_skipped_motion_total", "Frames skipped by motion gate")
frames_skipped_height    = Counter("pipeline_tracks_excluded_height_total", "Tracks excluded by height hard gate")
active_tracks            = Gauge("pipeline_active_tracks", "Current confirmed tracks")
inference_latency        = Histogram("pipeline_inference_latency_seconds", "Per-frame inference time",
                                     buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0])
fusion_score_dist        = Histogram("pipeline_fusion_score", "Fusion score distribution",
                                     buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
height_module_active     = Gauge("pipeline_height_module_active", "1 if height estimation is active")
height_consistent_ratio  = Gauge("pipeline_height_consistent_ratio", "Ratio of height-consistent tracks")
queue_depth              = Gauge("pipeline_queue_depth_frames", "Frames queued in Redis stream")

# Alert decision worker
alerts_generated         = Counter("pipeline_alerts_total", "Alerts written to Supabase", ["priority"])
temporal_rejections      = Counter("pipeline_temporal_rejections_total", "Candidates rejected by temporal validator")
behavioural_escalations  = Counter("pipeline_behavioural_escalations_total", "Alerts escalated by behaviour agent")

# Audit / integrity
audit_chain_intact       = Gauge("pipeline_audit_chain_intact", "1 if chain intact, 0 if tampered")

# Device health
device_last_seen         = Gauge("pipeline_device_last_seen_seconds_ago", "Seconds since last frame", ["device_id"])
device_transmission_failures = Counter("pipeline_device_transmission_failures_total", "ESP32 transmission failures", ["device_id"])
```

Metrics are exposed on port 9090 at `/metrics`. Accessible only from the monitoring subnet.

### 15.2 Edge Device Health

The ESP32 transmits a heartbeat POST to `/api/ingest/heartbeat` every 30 seconds when no frames are being transmitted. The heartbeat payload includes: WiFi RSSI, free PSRAM, queue depth, consecutive transmission failures, and firmware version. This data populates the `device_last_seen` and `device_transmission_failures` Prometheus metrics.

### 15.3 Calibration Drift Detection

A permanent calibration fixture (a reflective marker strip at a known height and known floor position) is required in the camera's field of view during installation. Its pixel position and size in a reference frame are recorded at calibration time.

The nightly calibration health check:
1. Requests a calibration frame from the device via MQTT.
2. Runs the pose model to detect the fixture.
3. Measures the fixture's pixel height.
4. Computes the implied `focal_length_px`.
5. Compares against the stored value. If deviation > 5%, marks calibration as drifted.

### 15.4 Structured Logging

All processes use JSON-structured logging:

```python
import logging, json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
            "timestamp": self.formatTime(record),
            "module":    record.module,
        })
```

Logs are routed to CloudWatch Logs (AWS) or equivalent structured log sink. Face scores, raw embeddings, and person crops are never logged. Track IDs and fusion scores may be logged at `DEBUG` level only.

### 15.5 Health Check Endpoints

```python
@app.route("/live")
def liveness():
    return jsonify(status="alive"), 200

@app.route("/ready")
def readiness():
    state_raw = redis.get("pipeline:state")
    if state_raw is None:
        return jsonify(status="not_ready", reason="no_inference_state"), 503
    state = json.loads(state_raw)
    age = time.time() - state["timestamp"]
    if age > 5.0:
        return jsonify(status="not_ready", reason=f"stale_state_{age:.1f}s"), 503
    return jsonify(status="ready", last_frame_age_s=round(age, 2)), 200
```

The `/ready` threshold is 5 seconds (not 2 seconds) to account for the ESP32's 500 ms inter-frame interval and network jitter. A 5-second-old pipeline state is not stale for this system's input rate.

---

## 16. Final Execution Flow

This section defines the complete authoritative runtime sequence. Every step is deterministic. Every branch is resolved.

```
────────────────────────────────────────────────────────────────────────
SYSTEM STARTUP
────────────────────────────────────────────────────────────────────────

[Process 3 — API server]
  1. Load environment variables.
  2. Initialise Flask app with JWT manager (JWT_SECRET_KEY, DEVICE_JWT_SECRET).
  3. Connect to Redis (read-only operations).
  4. Connect to Supabase with SUPABASE_ANON_KEY.
  5. Register all routes. Apply @jwt_required() to all data endpoints.
  6. Start Gunicorn (-w 4). Expose port 3000.
  7. /live returns 200 immediately.
  8. /ready returns 503 until pipeline:state exists in Redis.

[Process 2 — Alert decision worker]
  1. Load environment variables.
  2. Attempt to acquire Redis lock "lock:alert_decision_worker". If fails → exit(1).
  3. Connect to Supabase with SUPABASE_SERVICE_ROLE_KEY.
  4. Initialise TemporalValidator, BehavioralAnomalyAgent, ExplainabilityEngine.
  5. Load regions_of_interest.json.
  6. Open AlertAuditLog at runtime/audit/alert_chain.jsonl.
  7. Create Redis consumer group on stream:alert_candidates (if not exists).
  8. Enter processing loop (see ALERT DECISION LOOP below).

[Process 1 — Inference worker]
  1. Load environment variables.
  2. Load CameraCalibration for all registered devices from Supabase.
     → If any active device has no calibration AND production mode: log CRITICAL, exit(1).
     → If --skip-height-calibration: log WARNING, continue with height disabled.
  3. Load target profiles + face embeddings from Supabase (keyed by person_id).
  4. Verify embedding file signatures (HMAC). If any signature fails: log CRITICAL, exit(1).
  5. Load YOLO, DeepSORT, YOLOv8-pose, InsightFace models.
     → If YOLOv8-pose fails: log CRITICAL, set height_module_active=0, continue.
     → If InsightFace fails: log CRITICAL, exit(1). Face recognition is not optional.
  6. Initialise MotionGate, FaceExtractorNode, ReIDAgent, FusionEngine.
  7. Create Redis consumer group on stream:frames:incoming (if not exists).
  8. Subscribe to Supabase realtime for target_profiles and camera_calibrations updates.
  9. Log "[STARTUP] Inference worker ready. Tracker: deepsort. Height: active/disabled."
  10. Write initial pipeline:state to Redis.
  11. Enter processing loop (see INFERENCE LOOP below).

────────────────────────────────────────────────────────────────────────
INFERENCE LOOP (Process 1 — runs continuously)
────────────────────────────────────────────────────────────────────────

  LOOP:

  [Frame receipt]
  A. Read next frame from Redis stream:frames:incoming via XREADGROUP.
     Block for up to 1000 ms. If no frame: write heartbeat to pipeline:state. CONTINUE.
  B. Decode base64 JPEG to NumPy array (640×480×3).
  C. Read device_id from frame metadata. Look up CameraCalibration for device_id.
  D. Acknowledge frame in Redis stream (XACK).

  [Motion gate]
  E. Run MotionGate.should_process(frame).
     → False: call tracker.update(detections=[]) to advance Kalman state.
               Update pipeline:state. CONTINUE.
     → True: proceed to F.

  [Detection and tracking]
  F. Run YOLOv8 person detection. Get bounding boxes.
  G. Run DeepSORT.update(bboxes, frame). Get confirmed_tracks, lost_track_ids.
  H. Call FaceExtractorNode.on_tracks_lost(lost_track_ids).
     Call ReIDAgent.on_track_lost(descriptor) for each lost track.

  [Per-track processing]
  FOR EACH track IN confirmed_tracks:

    [Re-ID check for new tracks]
    I. If track.is_new:
         inherited_identity = ReIDAgent.on_track_confirmed(
             track_id, centroid, clothing_histogram)
         If inherited_identity is not None:
             → set prior_identity = inherited_identity
             → force fresh face comparison (bypass cache)

    [Feature extraction — parallel]
    J. Face: FaceExtractorNode.get_cached(track_id)
             If None: run InsightFace on face crop. Cache result (30s TTL).
             Compute face_score = max cosine similarity vs zone target profiles.

    K. Clothing: compute HSV histogram on person crop.
                 Compute clothing_score vs target profile hints.

    L. Height: if height_module_active AND calibration.calibrated:
                 Run YOLOv8-pose on full frame.
                 Extract crown + ankle keypoints for this track's bbox region.
                 If pose_confidence < 0.50 OR lower-body keypoints missing
                 OR seated/crouching geometry detected:
                   → height_estimate_m = None. height_confidence = 0.
                 Else:
                   → pixel_height = crown_y - ankle_y (pixels)
                   → height_estimate_m = calibration.pixel_height_to_meters(pixel_height)
                   → height_confidence = pose_confidence
               Else:
                   → height_estimate_m = None. height_confidence = 0.

    [Pre-fusion height gate]
    M. action, height_consistent, height_penalty = evaluate_height_gate(
           height_estimate_m,
           profile.reference_height_m,
           height_confidence,
           calibration.calibrated)
       If action == "exclude":
           → Increment pipeline_tracks_excluded_height_total.
           → Log at DEBUG. CONTINUE to next track.

    [Fusion]
    N. result = FusionEngine.fuse(FusionInput(
           face_score=face_score,
           clothing_score=clothing_score,
           height_consistent=height_consistent,
           height_penalty_applied=height_penalty_applied))

    [Candidate emission]
    O. If result.fusion_score >= 0.45 AND result.alert_level != "suppressed":
           redis.xadd("stream:alert_candidates", {
               "track_id": track_id,
               "device_id": device_id,
               "person_id": matched_person_id,
               "fusion_score": result.fusion_score,
               "alert_level": result.alert_level,
               "priority": result.priority,
               "height_consistent": height_consistent,
               "height_penalty_applied": height_penalty_applied,
               "height_estimate_m": height_estimate_m,
               "height_calibrated": calibration.calibrated,
               "face_score": face_score,
               "clothing_score": clothing_score,
               "clothing_color": dominant_color,
               "frame_timestamp": metadata.timestamp_ms,
               "payload": json.dumps(full_candidate_payload)
           })

  [State update]
  P. redis.setex("pipeline:state", 2, json.dumps({
         "timestamp": time.time(),
         "active_tracks": len(confirmed_tracks),
         "last_frame_device_id": device_id,
         "motion_ratio": motion_gate.last_ratio,
         "alert_candidates_pending": redis.xlen("stream:alert_candidates")
     }))

  END LOOP

────────────────────────────────────────────────────────────────────────
ALERT DECISION LOOP (Process 2 — runs continuously)
────────────────────────────────────────────────────────────────────────

  LOOP:

  A. Read up to 10 candidates from stream:alert_candidates via XREADGROUP.
     Block for up to 500 ms. If none: renew distributed lock. CONTINUE.

  FOR EACH candidate:

    B. Parse payload JSON.

    C. TemporalValidator.update(track_id, fusion_score, frame_timestamp).
       If track has fewer than TEMPORAL_MIN_FRAMES (3) above CANDIDATE_THRESHOLD (0.45)
       in the last TEMPORAL_WINDOW_FRAMES (10):
           → XACK stream:alert_candidates candidate_id. CONTINUE.

    D. BehavioralAnomalyAgent.score(track_behavior).
       If escalate_priority AND candidate.priority in ("low", "medium"):
           → candidate.priority = "high"

    E. Build AlertExplanation with all signal values including height metadata.

    F. alert_payload = assemble_full_alert_payload(candidate, explanation)
       payload_hash = audit_log.append(alert_payload)
       alert_payload["payload_hash"] = payload_hash

    G. Write to Supabase alerts table with exponential backoff retry.
       If Supabase unavailable: retain in audit log. Retry on next loop.

    H. If alert_level == "confirmed":
           redis.publish(f"mqtt:devices:{device_id}:control",
                         json.dumps({"cmd": "alert_session_start"}))
           # MQTT bridge forwards to device

    I. XACK stream:alert_candidates candidate_id.

  END LOOP

────────────────────────────────────────────────────────────────────────
END OF AUTHORITATIVE EXECUTION FLOW
────────────────────────────────────────────────────────────────────────
```

---

*This document is the sole authoritative specification for the IoT Surveillance System v3.0. All code, configuration, firmware, and infrastructure must conform to this specification. Deviations require a formal specification amendment — not a code-only change.*

*Supersedes: DEPLOYMENT_SPEC.md v1.0, DEPLOYMENT_SPEC_CORRECTED.md v2.0, all pipeline.md revisions.*
