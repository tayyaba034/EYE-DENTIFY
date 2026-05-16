# Surveillance Pipeline Detection Scope & Pose Landmarks Issue

## What Does This Pipeline Detect?

**🔍 PERSONS (People/Humans) — NOT Faces**

### Detection Focus:
- **YOLOv8 Person Detector** (Stage 1)
- Detects COCO class `person` (people/humans in images/video)
- Uses bounding boxes: `[x, y, width, height]`
- Confidence threshold: 0.50 (default)
- No per-person labelling or identification at detection stage

### What Gets Tracked:
- Bounding boxes of detected persons
- Track IDs (for continuity across frames)
- NOT individual face identification at detection level

### What About Faces?
- **Faces are extracted AFTER tracking** (Stage 3A)
- Only analyzed from confirmed tracks (people detected + tracked)
- Face recognition is SECONDARY — optional feature
- Can be disabled with `--face-mode none`

---

## Pose Landmarks Issue — Why They're Not Showing

### Root Causes:

#### 1. **Pose Model Not Loaded**
   - Default path: `height_estimation_module/yolov8n-pose.pt`
   - If missing → falls back to bounding box heuristic
   - Check: `File exists and readable?`

#### 2. **MediaPipe Landmarker Missing** 
   - Enhanced pose requires: `mediapipe` package
   - Model file: `height_estimation_module/models/pose_landmarker.task`
   - If missing → uses YOLO pose only
   - **Current environment doesn't have MediaPipe installed**

#### 3. **Confidence Thresholds Too High**
   In `height_estimation_module/estimator.py`:
   ```python
   # YOLO pose requires:
   nose_confidence > 0.5  # Head detection must be strong
   ankle_confidence > 0.5 # At least one foot must be visible
   
   # MediaPipe requires:
   min_pose_detection_confidence=0.45
   min_pose_presence_confidence=0.45
   min_tracking_confidence=0.45
   ```
   
   If pose is detected but confidence is low → landmarks not returned

#### 4. **Incomplete Pose in Frame**
   - Person partially out of frame
   - Head or feet not visible
   - Extreme angle/occlusion
   - → Falls back to bbox-based height estimate

---

## Pipeline Detection Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: PERSON DETECTION (YOLOv8)                         │
│ Input: Raw video frame                                      │
│ Detection: COCO person class bounding boxes                 │
│ Output: [x, y, w, h] for each detected person              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: MULTI-OBJECT TRACKING (ByteTrack)                 │
│ Input: Detection boxes                                      │
│ Tracking: Assign track_ids to maintain continuity           │
│ Output: confirmed_tracks with track_id                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3A: FACIAL RECOGNITION (Optional - InsightFace)      │
│ Input: Person bounding box + frame                          │
│ Detection: Face inside person bbox                          │
│ Analysis: Face embedding + score matching                   │
│ Output: face_score (0-1) for identity matching              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3B: CLOTHING EXTRACTION (Always active)               │
│ Input: Person bounding box + frame                          │
│ Analysis: Color/clothing in torso region                    │
│ Output: clothing_score (0-1)                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3C: HEIGHT ESTIMATION (Optional - YOLOv8 Pose)        │
│ Input: Person bounding box + frame                          │
│ Detection: Pose keypoints (nose, ankles, etc)               │
│ Calculation: Height from pose landmarks                     │
│ Fallback: Bbox-based height estimate                        │
│ Output: height_score (0-1) + landmarks array                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: MULTI-ATTRIBUTE FUSION                             │
│ Input: face_score + clothing_score + height_score           │
│ Fusion: Weighted combination                                │
│ Output: final_score (0-1) per tracked person                │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Landmarks Are Empty in JSON Output

### Example Output Structure:
```json
{
  "height": {
    "estimated_height_m": 1.75,
    "confidence": 0.35,
    "pose_detected": false
  },
  "landmarks": []  // ← EMPTY because no pose detected
}
```

### When Landmarks ARE Populated:
```json
{
  "height": {
    "estimated_height_m": 1.82,
    "confidence": 0.85,
    "pose_detected": true
  },
  "landmarks": [
    {"id": 0, "x": 640, "y": 120, "visibility": 0.92},   // Nose
    {"id": 15, "x": 580, "y": 480, "visibility": 0.88},  // Left ankle
    {"id": 16, "x": 700, "y": 480, "visibility": 0.91},  // Right ankle
    ...
  ]
}
```

---

## How to Fix Pose Landmarks

### Option 1: Lower Confidence Thresholds
Edit `height_estimation_module/estimator.py`:
```python
# Change from:
if person_confs[0] <= 0.5 or (person_confs[15] <= 0.5 and person_confs[16] <= 0.5):
    return None, [], 0.0

# To:
if person_confs[0] <= 0.3 or (person_confs[15] <= 0.3 and person_confs[16] <= 0.3):
    return None, [], 0.0
```

### Option 2: Install MediaPipe for Enhanced Pose
```bash
pip install mediapipe>=0.8.11
```
Then add `pose_landmarker.task` to `height_estimation_module/models/`

### Option 3: Verify Pose Model Exists
```bash
ls -la height_estimation_module/yolov8n-pose.pt
# Should return the file, not "file not found"
```

### Option 4: Debug Output
Add logging to see what's happening:
```python
# In height_estimation_module/estimator.py
def _pose_height_from_crop(self, crop, x1, y1):
    if self.pose_model is None:
        print("❌ POSE MODEL NOT LOADED")  # ← Add this
        return None, [], 0.0
    
    result = self.pose_model(crop, verbose=False)[0]
    if result.keypoints is None:
        print("❌ NO KEYPOINTS DETECTED")  # ← Add this
        return None, [], 0.0
    
    print(f"✅ Found {len(result.keypoints.xy[0])} keypoints")  # ← Add this
```

---

## Current Pipeline Capabilities

### ✅ Always Active:
- Person detection (YOLO)
- Person tracking (ByteTrack)
- Clothing analysis
- Temporal validation
- Alert decision engine

### 🔧 Optional/Conditional:
- Face recognition (InsightFace) — `--face-mode recognition`
- Height estimation (YOLO Pose) — Falls back gracefully
- Enhanced pose (MediaPipe) — If installed
- ArUco calibration — If markers in frame

### ❌ Not Supported:
- Individual person re-identification across cameras (REID)
- Facial landmarks (uses pose instead)
- Real-time facial expression analysis

---

## Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **What detects?** | Persons | COCO person class, not faces |
| **Faces detected?** | Yes, secondary | Only from confirmed tracked persons |
| **Landmarks showing?** | Empty/low conf | Pose confidence too high or model not loaded |
| **Fallback exists?** | Yes | Uses bbox-based height if pose fails |
| **Can be fixed?** | Yes | Lower thresholds or install MediaPipe |

