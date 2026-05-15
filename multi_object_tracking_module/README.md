# Multi-Object Tracking Module
**Surveillance Intelligence Pipeline — Stage 2 of 7**

---

## Purpose

Assign and maintain **persistent `track_id`s** to detected persons across frames.  
Receives bounding boxes from Stage 1 (Person Detection).  
Outputs stable tracked objects to Stage 3 (Feature Extraction).

**Strictly no** recognition, identity labelling, or decision-making.

---

## File Structure

```
multi-object-tracking-module/
├── __init__.py            ← Public API
├── config.py              ← All tunable parameters
├── tracker.py             ← Backend-agnostic tracker orchestrator
├── bytetrack_adapter.py   ← ByteTrack implementation (default)
├── deepsort_adapter.py    ← DeepSORT implementation (optional)
├── schemas.py             ← Output dataclass schemas
├── requirements.txt       ← Dependencies
└── README.md              ← This file
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```python
from person_detection_module import PersonDetector
from multi_object_tracking_module import MultiObjectTracker

detector = PersonDetector()
tracker  = MultiObjectTracker(backend="bytetrack")   # or "deepsort"

frame_id = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break

    detection_output = detector.detect(frame, frame_id)
    tracking_output  = tracker.update(detection_output, frame=frame)

    # Only confirmed stable tracks go to Stage 3
    for track in tracking_output.confirmed_tracks:
        print(track.to_dict())

    frame_id += 1
```

---

## Output Schema

```json
{
  "frame_id": 42,
  "tracks": [
    {
      "track_id": 7,
      "bbox": [120.5, 85.0, 95.0, 210.0],
      "confidence": 0.8741,
      "state": "confirmed",
      "frames_seen": 12
    }
  ]
}
```

| Field | Description |
|---|---|
| `track_id` | Persistent integer ID across frames |
| `bbox` | `[x, y, width, height]` in pixels |
| `confidence` | Detection confidence from Stage 1 |
| `state` | `confirmed` / `tentative` / `lost` |
| `frames_seen` | Consecutive frames observed |

> Only `state == "confirmed"` tracks are forwarded to Feature Extraction.

---

## Tracker Backends

### ByteTrack (default, recommended)
- IoU-based two-pass matching (high + low confidence detections)
- Kalman filter for position prediction during occlusion
- No appearance features required
- Set `TRACKER_BACKEND = "bytetrack"` in `config.py`

### DeepSORT
- Kalman filter + CNN re-ID appearance embeddings
- Stronger re-association after long occlusions
- Requires raw frame for embedding extraction
- Set `TRACKER_BACKEND = "deepsort"` in `config.py`

---

## Configuration (`config.py`)

| Parameter | Default | Description |
|---|---|---|
| `TRACKER_BACKEND` | `bytetrack` | Active backend |
| `BT_TRACK_THRESH` | `0.50` | High-conf detection threshold |
| `BT_TRACK_BUFFER` | `30` | Frames to hold lost track |
| `BT_MATCH_THRESH` | `0.80` | IoU match threshold |
| `DS_MAX_AGE` | `30` | DeepSORT: frames before track deletion |
| `DS_N_INIT` | `3` | DeepSORT: frames before confirmation |
| `MAX_FRAMES_MISSING` | `30` | Occlusion hold duration |

---

## Track Lifecycle

```
New detection → TENTATIVE (age 1-2)
                    ↓ (≥3 consecutive matches)
              CONFIRMED  ←──── matched detection
                    ↓ (missed frames)
                  LOST  ────── held for MAX_FRAMES_MISSING
                    ↓ (timeout)
                 PRUNED (removed from state)
```

---

## Failure Handling

| Condition | Behaviour |
|---|---|
| Detection missing 1-N frames | Track held alive (LOST state) |
| Detection missing > MAX_FRAMES_MISSING | Track pruned cleanly |
| Ambiguous IoU match | Track NOT reassigned — identity preserved |
| No detections in frame | Returns empty tracks list |

---

## Pipeline Integration

```
Stage 1: PersonDetector.detect(frame, frame_id)
              ↓  FrameDetectionOutput
Stage 2: MultiObjectTracker.update(detection_output, frame)
              ↓  FrameTrackingOutput (confirmed_tracks)
Stage 3: Feature Extraction (Face + Clothing)
```
