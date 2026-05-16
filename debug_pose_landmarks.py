#!/usr/bin/env python
"""
Debug script to check why pose landmarks are not appearing in the pipeline.
Run this to diagnose height estimation issues.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def check_pose_model():
    """Check if the pose model file exists."""
    model_path = Path("height_estimation_module/yolov8n-pose.pt")
    print(f"\n{'='*60}")
    print("1. POSE MODEL CHECK")
    print(f"{'='*60}")
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"✅ Pose model found: {model_path}")
        print(f"   Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ Pose model NOT found: {model_path}")
        print("   Action: Download yolov8n-pose.pt from Ultralytics")
        return False


def check_mediapipe():
    """Check if MediaPipe is installed and landmarker model exists."""
    print(f"\n{'='*60}")
    print("2. MEDIAPIPE & LANDMARKER CHECK")
    print(f"{'='*60}")
    
    try:
        import mediapipe
        print(f"✅ MediaPipe installed: version {mediapipe.__version__}")
    except ImportError:
        print("⚠️  MediaPipe NOT installed (optional for enhanced pose)")
        print("   Install: pip install mediapipe>=0.8.11")
    
    landmarker_path = Path("height_estimation_module/models/pose_landmarker.task")
    if landmarker_path.exists():
        size_mb = landmarker_path.stat().st_size / (1024 * 1024)
        print(f"✅ Landmarker model found: {landmarker_path}")
        print(f"   Size: {size_mb:.1f} MB")
    else:
        print(f"⚠️  Landmarker model NOT found: {landmarker_path}")
        print("   Using YOLO pose as fallback (still works)")


def check_estimator():
    """Test the HeightEstimator initialization."""
    print(f"\n{'='*60}")
    print("3. HEIGHT ESTIMATOR INITIALIZATION")
    print(f"{'='*60}")
    
    try:
        from height_estimation_module import HeightEstimator
        
        estimator = HeightEstimator()
        print("✅ HeightEstimator initialized successfully")
        
        if estimator.pose_model is not None:
            print("✅ YOLO Pose model loaded")
        else:
            print("❌ YOLO Pose model FAILED to load")
            print("   Check: yolov8n-pose.pt exists and is readable")
        
        if estimator._landmarker is not None:
            print("✅ MediaPipe Landmarker loaded")
        else:
            print("⚠️  MediaPipe Landmarker not available (fallback to YOLO)")
        
        if estimator._aruco_ready:
            print("✅ ArUco marker detection available")
        else:
            print("⚠️  ArUco not available (optional feature)")
            
    except Exception as e:
        print(f"❌ ERROR initializing HeightEstimator: {e}")
        import traceback
        traceback.print_exc()


def check_detection():
    """Simulate detection and track through the pipeline."""
    print(f"\n{'='*60}")
    print("4. PIPELINE DETECTION FLOW TEST")
    print(f"{'='*60}")
    
    try:
        import cv2
        from person_detection_module.detector import PersonDetector
        from multi_object_tracking_module.tracker import MultiObjectTracker
        
        print("✅ Detector imported successfully")
        print("✅ Tracker imported successfully")
        
        # Check what the detector is looking for
        detector = PersonDetector()
        print(f"\n📊 PersonDetector Configuration:")
        print(f"   • Detection class: COCO 'person' (class ID: 0)")
        print(f"   • Confidence threshold: {detector.conf_threshold}")
        print(f"   • Model path: {detector.model_path}")
        
    except Exception as e:
        print(f"❌ ERROR loading detector: {e}")
        import traceback
        traceback.print_exc()


def explain_landmarks():
    """Explain why landmarks might be empty."""
    print(f"\n{'='*60}")
    print("5. WHY LANDMARKS ARE EMPTY - DIAGNOSTICS")
    print(f"{'='*60}")
    
    print("""
YOLO Pose Landmarks Requirements:
─────────────────────────────────
✓ Person must be fully visible in frame (or mostly visible)
✓ Head/nose confidence > 0.5 (default threshold)
✓ At least one foot/ankle confidence > 0.5
✓ Pose keypoints detected successfully

Common Reasons for Empty Landmarks:
──────────────────────────────────
1. Person partially out of frame
   → Head/feet not visible enough
   
2. Person at extreme angle
   → Pose model confidence drops below threshold
   
3. Person occluded or blurry
   → Keypoints not detectable
   
4. Pose model not loaded
   → Falls back to bbox-based height estimate
   
5. Confidence threshold too high (currently 0.5)
   → Lower it in estimator.py if too conservative

Detection Focus:
────────────────
❌ NOT faces/faces detection
❌ NOT facial landmarks
✅ Persons/people detection (COCO class)
✅ Pose keypoints (if full body visible)
✅ Person tracking across frames
    """)


def main():
    """Run all diagnostics."""
    print("\n" + "="*60)
    print("PIPELINE DIAGNOSTICS - POSE LANDMARKS & DETECTION")
    print("="*60)
    
    check_pose_model()
    check_mediapipe()
    check_estimator()
    check_detection()
    explain_landmarks()
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print("""
Pipeline Detection Summary:
───────────────────────────
This pipeline detects PERSONS (people), not faces.

Flow:
1. Detect persons (YOLO)           → Bounding boxes
2. Track persons (ByteTrack)       → Track IDs
3. Extract clothing features       → Color analysis
4. Estimate height from pose       → Pose keypoints
5. Detect faces (optional)         → Face recognition
6. Fuse all signals                → Final score
7. Temporal validation             → Stability check
8. Alert decision                  → Alert threshold

Empty Landmarks Reasons:
────────────────────────
• Pose confidence too low
• Person not fully visible
• Model not loaded

Next Steps:
───────────
1. Run full pipeline: python surveillance_live_service.py --source 0
2. Check JSON output in runtime/artifacts/latest_pipeline_output.json
3. Look for "landmarks" array (may be empty if pose fails)
4. Review "pose_detected" flag (true/false)
    """)


if __name__ == "__main__":
    main()
