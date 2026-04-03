# EYE-DENTIFY

> **Smart AI-Based Surveillance System** — Real-time person identification through a multi-stage AI pipeline, cross-platform mobile client, and live admin dashboard.

---

## Overview

EYE-DENTIFY is an end-to-end intelligent surveillance platform that detects and identifies a specific individual in a live camera feed using a fusion of facial recognition, clothing analysis, and height estimation. Alerts are stored in Supabase and surfaced through both a web dashboard and a Flutter mobile app.

```
Camera Feed → Detection → Tracking → Feature Extraction → Fusion → Validation → Alert → Dashboard
```

---

## Key Features

- **YOLOv8s Person Detection** — fast, accurate human detection from any camera source
- **DeepSORT Multi-Object Tracking** — persistent track IDs across frames
- **InsightFace Facial Verification** — cosine-similarity-based biometric matching
- **Clothing Feature Extraction** — dominant color analysis as a secondary identity signal
- **Height Estimation** — optional body geometry signal to reinforce uncertain matches
- **Multi-Attribute Fusion** — combines all signals into a single confidence score
- **Temporal Validation** — rejects unstable one-frame detections
- **Alert Decision Engine** — converts model output into actionable security alerts
- **Explainability Layer** — human-readable summary of why each alert was triggered
- **Supabase Integration** — alerts written to and read from a shared cloud database
- **Live Web Dashboard** — real-time pipeline state, alert queue, and stream overlay
- **Flutter Mobile App** — cross-platform client reading from the same Supabase schema

---

## System Architecture

```
Camera Feed
   │
   ▼
┌──────────────────────────┐
│  1. Perception           │  YOLOv8s — detects persons, outputs bounding boxes
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  2. Memory & Continuity  │  DeepSORT — assigns persistent track IDs across frames
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  3. Feature Extraction   │
│   ├─ Face Verification   │  InsightFace — cosine similarity against known database
│   ├─ Clothing Features   │  Dominant color extraction (normalized color categories)
│   └─ Height Estimation   │  Body geometry estimation (optional signal)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  4. Fusion               │  Combines face + clothing + height into one score
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  5. Temporal Validation  │  Requires confidence stability across consecutive frames
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  6. Alert Decision       │  Assigns alert / no-alert with priority level
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  7. Explainability       │  Human-readable evidence summary
│  +  Output Delivery      │  Writes alert + snapshot to Supabase
└──────────┬───────────────┘
           │
           ▼
  Web Dashboard + Flutter App
```

---

## Module Map

| Stage | Module |
|---|---|
| Person Detection | `person_detection_module` |
| Multi-Object Tracking | `multi_object_tracking_module` |
| Face Verification | `facial_recognition_module` |
| Clothing Features | `clothing_feature_extraction_module` |
| Height Estimation | `height_estimation_module` |
| Signal Fusion | `multi_attribute_fusion_module` |
| Temporal Validation | `temporal_validation_module` |
| Alert Decision | `alert_decision_module` |
| Explainability | `explainability_module` |
| Output Delivery | `output_delivery_module` |
| Pipeline Coordinator | `surveillance_backend_pipeline.py` |
| Live API + Dashboard | `surveillance_live_service.py` |

---

## Getting Started

### Prerequisites

- Python 3.9+
- CUDA-compatible GPU (recommended)
- Node.js (for dashboard frontend)
- Flutter SDK (for mobile app)
- Supabase account and project

### Installation

```bash
git clone https://github.com/your-username/eye-dentify.git
cd eye-dentify
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

---

## Running the Pipeline

### Detection Only

```bash
cd person_detection_module
python run_detection.py                         # webcam
python run_detection.py --source "video.mp4"   # video file
python run_detection.py --source "image.jpg"   # image
python run_detection.py --conf 0.65            # custom confidence
```

### Tracking Only

```bash
cd multi_object_tracking_module
python run_tracking.py --source 0              # webcam
python run_tracking.py --source "video.mp4"   # video file
```

### Full Backend Pipeline

```bash
python run_surveillance_pipeline.py --source 0
```

### Live Service + Dashboard

```bash
python surveillance_live_service.py --source 0
```

### IP Camera / CCTV / RTSP Stream

```bash
python surveillance_live_service.py --source "rtsp://username:password@camera-ip:554/stream"
```

---

## Dashboard

The web dashboard provides:

- **Live stream overlay** with bounding boxes and track IDs
- **Track list** showing currently active persons
- **Fusion summary** per tracked individual
- **Alert queue** with timestamps and priority levels
- **Delivery log** of alerts written to Supabase

---

## Flutter Mobile App

The Flutter client connects to the same Supabase backend and provides:

- Recent alert history with metadata
- Live pipeline status
- (Optional) Push notifications for new alerts
- (Optional) Role-based access and authentication

---

## Database Schema (Supabase)

All alerts are written to Supabase and shared across the web dashboard and mobile app. The backend is the sole writer; both clients are read-only consumers of the same schema.

Key fields in each alert record:

- `track_id` — DeepSORT persistent ID
- `face_score` — cosine similarity from InsightFace
- `clothing_color` — normalized dominant color
- `fused_score` — final combined confidence
- `priority` — alert priority level
- `snapshot_url` — cropped image if available
- `timestamp` — UTC time of alert
- `explanation` — human-readable evidence summary

---

## Project Roadmap

| Phase | Description | Status |
|---|---|---|
| **1** | Core AI Vision Pipeline | ✅ Mostly complete |
| **2** | Supabase Database Integration | ✅ Connected |
| **3** | Flutter Mobile Application | 🔄 In progress |
| **4** | External Camera Integration (USB / IP / RTSP / Raspberry Pi) | 📋 Planned |
| **5** | AWS Cloud Deployment | 📋 Planned |
| **6** | Full End-to-End Integration Testing | 📋 Planned |
| **7** | Production Hardening & Documentation | 📋 Planned |

---

## External Camera Support

The pipeline supports multiple camera sources:

- **USB / External Webcam** — use `--source 0`, `--source 1`, etc.
- **IP Camera / CCTV** — pass RTSP or HTTP stream URL as `--source`
- **Raspberry Pi** — use Pi as the capture node; run inference on the backend server or AWS

For Raspberry Pi deployments, the recommended architecture is:

```
Raspberry Pi (capture) → Network → Backend Server (AI inference) → Supabase
```

---


# Mental Model

```
YOLO says:              "There is a person here."
DeepSORT says:          "This is the same person I saw before."
Face/Clothing/Height:   "These are the attributes of that tracked person."
Fusion says:            "Here is the combined confidence."
Temporal Validation:    "This confidence stayed stable long enough."
Alert Decision says:    "This now deserves an alert."
Explainability says:    "Here is why."
Delivery says:          "Store it, show it, and send it."
```

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

##  Author

Built as a Final Year Project (FYP) an end-to-end AI surveillance system with real-time person identification, cloud alerting, and cross-platform client support.
