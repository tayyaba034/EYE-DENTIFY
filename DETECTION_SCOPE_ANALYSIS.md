# Pipeline Detection Scope & Pose Landmarks - DIAGNOSIS

## ❓ What Does This Pipeline Detect?

### **Answer: PERSONS (People/Humans) — NOT Faces at Detection Stage**

```
Input: Video/Image
  ↓
Stage 1: Person Detection (YOLOv8 COCO)
  ├─ Detects: PEOPLE with bounding boxes
  ├─ NOT detecting: Faces, objects, animals
  ├─ Confidence: 50% default
  └─ Output: [x, y, width, height] per person
  ↓
Stage 2: Multi-Object Tracking (ByteTrack)
  ├─ Assigns: Unique track_id to each person
  ├─ Maintains: Continuity across frames
  └─ Output: Confirmed tracks with IDs
  ↓
Stage 3: Feature Extraction (Parallel)
  ├─ 3A Faces (Optional): Extract faces FROM confirmed person tracks
  ├─ 3B Clothing: Analyze torso color/clothing
  └─ 3C Height: Estimate from pose keypoints
  ↓
Stage 4-7: Fusion → Validation → Alerting → Delivery
```

---

## ❓ Why Are Landmarks Empty?

### **Answer: YOLO Pose Model Failed to Load**

From the diagnostic run:
```
❌ YOLO Pose model FAILED to load
   Check: yolov8n-pose.pt exists and is readable
```

### Root Cause:
The pose model file exists (`6.5 MB`), but **PyTorch is not installed** in your Python environment.

### Why:
```python
# height_estimation_module/estimator.py tries:
from ultralytics import YOLO
yolo_model = YOLO("yolov8n-pose.pt")
# ← This requires PyTorch, which isn't in your env
```

### Consequence:
When pose model fails to load:
1. Falls back to **bbox-based height estimation** (less accurate)
2. Returns **empty landmarks array** `[]`
3. Sets `pose_detected = false`

---

## 🔧 How to Fix Landmarks

### Option 1: Install PyTorch (Recommended)
```bash
# CPU version (faster to install)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# OR GPU version (if you have CUDA)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Then verify:
```bash
python -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
```

### Option 2: Install MediaPipe for Better Pose
```bash
pip install mediapipe>=0.8.11
```

Current status:
- ✅ Model file exists: `height_estimation_module/models/pose_landmarker.task` (5.5 MB)
- ❌ MediaPipe not installed
- With MediaPipe: Better pose detection + more robust

### Option 3: Lower Confidence Thresholds
If you want quicker results without full dependencies:

```python
# Edit: height_estimation_module/estimator.py, line ~160

# Current (strict):
if person_confs[0] <= 0.5 or (person_confs[15] <= 0.5 and person_confs[16] <= 0.5):
    return None, [], 0.0

# Change to (lenient):
if person_confs[0] <= 0.25 or (person_confs[15] <= 0.25 and person_confs[16] <= 0.25):
    return None, [], 0.0
```

This will populate landmarks more often (even with lower confidence poses).

---

## 📊 What Gets Detected in Detail

### Stage 1: Person Detection
```json
{
  "detections": [
    {
      "bbox": [100, 50, 150, 300],  // x, y, w, h
      "confidence": 0.92,
      "class": "person"
    },
    {
      "bbox": [400, 100, 120, 280],
      "confidence": 0.87,
      "class": "person"
    }
  ]
}
```

**NOT detected:**
- Faces (no facial detection at this stage)
- Animals, vehicles, objects
- Partial people (too small or too blurry)

---

### Stage 3A: Face Analysis (From Confirmed Tracks)
```json
{
  "track_id": 1,
  "face_features": {
    "face_detected": true,
    "face_score": 0.82,
    "identity_match": "JOHN_DOE"  // optional
  }
}
```

**Only happens AFTER:**
- Person detected
- Person tracked (has track_id)
- Face box extracted from person bbox

---

### Stage 3C: Pose & Height (Current Issue)
```json
{
  "track_id": 1,
  "height": {
    "estimated_height_m": 1.75,
    "confidence": 0.35,
    "pose_detected": false  // ← This is FALSE because PyTorch missing
  },
  "landmarks": []  // ← Empty because pose_detected is false
}
```

**When PyTorch IS installed:**
```json
{
  "track_id": 1,
  "height": {
    "estimated_height_m": 1.82,
    "confidence": 0.85,
    "pose_detected": true  // ← TRUE when pose is detected
  },
  "landmarks": [
    {"id": 0, "x": 640, "y": 120, "visibility": 0.92},   // Nose
    {"id": 5, "x": 600, "y": 180, "visibility": 0.88},   // Left shoulder
    {"id": 6, "x": 680, "y": 180, "visibility": 0.91},   // Right shoulder
    {"id": 11, "x": 550, "y": 350, "visibility": 0.85},  // Left hip
    {"id": 12, "x": 730, "y": 350, "visibility": 0.87},  // Right hip
    {"id": 15, "x": 580, "y": 480, "visibility": 0.88},  // Left ankle
    {"id": 16, "x": 700, "y": 480, "visibility": 0.91},  // Right ankle
    ...more landmarks...
  ]
}
```

---

## 🎯 Summary Table

| Question | Answer |
|----------|--------|
| **What is detected at Stage 1?** | PERSONS (people bounding boxes from COCO) |
| **Are faces detected at Stage 1?** | No, faces are extracted AFTER tracking |
| **When are faces analyzed?** | Stage 3A, only from confirmed person tracks |
| **Why are landmarks empty?** | PyTorch not installed → Pose model fails to load |
| **Can it be fixed?** | Yes, install PyTorch or MediaPipe |
| **Is there a fallback?** | Yes, uses bbox-based height (less accurate) |
| **What does pose_detected=false mean?** | Pose keypoints not detected or confidence too low |

---

## 📋 Diagnostic Results from Your System

```
✅ Pose model file: height_estimation_module/yolov8n-pose.pt (6.5 MB)
❌ PyTorch: NOT installed (CAUSE OF LANDMARKS ISSUE)
⚠️  MediaPipe: NOT installed (optional enhancement)
✅ Landmarker: height_estimation_module/models/pose_landmarker.task (5.5 MB)
✅ ArUco markers: Available for calibration
```

---

## 🚀 Quick Fix

**Minimum install to get landmarks working:**
```bash
# Install PyTorch
pip install torch

# Then test
python debug_pose_landmarks.py
```

Expected output after fix:
```
✅ YOLO Pose model loaded
✅ HeightEstimator initialized successfully
```

Then when you run the pipeline, landmarks will populate automatically! 🎉

