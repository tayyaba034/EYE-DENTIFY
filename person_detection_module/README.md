# Person Detection Module
**Surveillance Intelligence Pipeline — Stage 1 of 7**

---

## Purpose

Detect all human figures in a video frame using YOLOv8.  
This module is **strictly limited** to detection — no identity, no tracking, no decisions.

---

## File Structure

```
person_detection_module/
├── __init__.py          ← Public API (PersonDetector, FrameDetectionOutput)
├── config.py            ← All tunable parameters
├── detector.py          ← Core YOLOv8 detection engine
├── temporal_smoother.py ← EMA-based flicker suppression
├── schemas.py           ← Output dataclass schemas
├── requirements.txt     ← Dependencies
└── README.md            ← This file
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```python
import cv2
from person_detection_module import PersonDetector

detector = PersonDetector(
    model_path="yolov8n.pt",
    conf_threshold=0.5,
    device="cuda",
    enable_smoothing=True,
)

cap = cv2.VideoCapture(0)
frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    output = detector.detect(frame, frame_id)
    print(output.to_json())
    frame_id += 1
```

---

## Output Schema

Matches the pipeline specification exactly:

```json
{
  "frame_id": 42,
  "detections": [
    {
      "bbox": [120.5, 80.2, 95.0, 210.3],
      "confidence": 0.8741
    }
  ]
}
```

- `bbox` → `[x, y, width, height]` — top-left corner + dimensions in pixels  
- `confidence` → float in `[0.0, 1.0]`  
- Empty `detections` array when no persons are found — **never null**

---

## Configuration (`config.py`)

| Parameter | Default | Description |
|---|---|---|
| `MODEL_PATH` | `yolov8n.pt` | YOLOv8 weights (n/s/m/l/x) |
| `CONFIDENCE_THRESHOLD` | `0.50` | Minimum detection confidence |
| `NMS_IOU_THRESHOLD` | `0.45` | IoU for Non-Max Suppression |
| `DEVICE` | `cuda` | Inference device |
| `SMOOTHING_WINDOW` | `3` | Frames before stale candidate is pruned |
| `MIN_CONSECUTIVE_FRAMES` | `2` | Frames a bbox must appear to be emitted |
| `IOU_MATCH_THRESHOLD` | `0.40` | IoU for linking bboxes across frames |

---

## Temporal Smoother

The `TemporalSmoother` in `temporal_smoother.py` suppresses flickering bboxes:

1. Incoming raw bboxes are matched to existing candidates via IoU.
2. Matched candidates are updated using **Exponential Moving Average (EMA)**.
3. Only candidates seen for ≥ `MIN_CONSECUTIVE_FRAMES` are emitted.
4. Candidates unseen for ≥ `SMOOTHING_WINDOW` frames are pruned.

> This is **detection-level smoothing only**. Multi-object tracking (Stage 2) handles identity persistence.

---

## Constraints (enforced)

- **NO** identity logic  
- **NO** tracking logic  
- **NO** assumptions about individuals  
- Returns empty array on zero detections — never fabricates results  

---

## Pipeline Integration

```
[Camera Feed]
      ↓
[PersonDetector.detect(frame, frame_id)]
      ↓
FrameDetectionOutput  ──→  Stage 2: Multi-Object Tracking (DeepSORT/ByteTrack)
```

---

## Failure Handling

| Condition | Behaviour |
|---|---|
| No persons detected | Returns `detections: []` — empty array |
| Null / empty frame | Returns `detections: []` with a warning log |
| Model load failure | Raises `RuntimeError` with clear message |
| Flickering detection | Suppressed by TemporalSmoother until stable |
