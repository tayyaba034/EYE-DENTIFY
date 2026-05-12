"""
run_face_node.py — Stage 3A Output Tester
Surveillance Intelligence Pipeline

Integration test testing Detection -> Tracking -> Facial Verification.
"""

import sys
import os
import argparse
import logging
import cv2
import json

# Ensure modules are importable from parent directory (up from src/ -> facial_recognition_module/ -> project root)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from person_detection_module.detector import PersonDetector
from multi_object_tracking_module.tracker import MultiObjectTracker
from facial_recognition_module.src.face_node import FaceExtractorNode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("stage3_test")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0")
    args = parser.parse_args()
    
    source = int(args.source) if args.source.isdigit() else args.source

    logger.info("Initialising Stage 1 (Detection)...")
    detector = PersonDetector(model_path="yolov8n.pt", conf_threshold=0.5)

    logger.info("Initialising Stage 2 (Tracking) with DeepSORT...")
    tracker = MultiObjectTracker(backend="deepsort")

    logger.info("Initialising Stage 3A (Facial Extraction Node)...")
    face_node = FaceExtractorNode()

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error("Cannot open source: %s", source)
        sys.exit(1)

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret: break

        # Stage 1: Detection
        det_out = detector.detect(frame, frame_id)
        
        # Stage 2: Tracking
        track_out = tracker.update(det_out, frame=frame)
        
        # Stage 3A: Face Extraction (Integration)
        face_results = face_node.process(track_out, frame)

        # Log exactly as user requested
        if frame_id % 15 == 0 and face_results:
            print("\n--- STAGE 3A OUTPUT ---")
            for r in face_results:
                print(json.dumps(r, indent=2))
        
        # Basic Visualization
        vis = frame.copy()
        
        # Draw tracks and faces
        for track in track_out.confirmed_tracks:
            x, y, w, h = [int(v) for v in track.bbox]
            cv2.rectangle(vis, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Find the matching face result
            for r in face_results:
                if r["track_id"] == track.track_id:
                    if r["face_detected"]:
                        score = r['face_score']
                        is_match = score >= 0.40 # Similarity Threshold
                        
                        label = f"ID:{track.track_id} Score:{score:.2f}"
                        # Green text if match, Red text if no match
                        text_color = (0, 255, 0) if is_match else (0, 0, 255)
                        cv2.putText(vis, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
                        
                        # Draw the isolated face bounding box if present
                        if "face_bbox" in r:
                            fx1, fy1, fx2, fy2 = r["face_bbox"]
                            # Green box if match, Red box if no match
                            box_color = (0, 255, 0) if is_match else (0, 0, 255)
                            cv2.rectangle(vis, (fx1, fy1), (fx2, fy2), box_color, 2)
                    else:
                        label = f"ID:{track.track_id} Face:No/Blurry"
                        cv2.putText(vis, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw HUD on Top-Left Corner
        hud_stage1 = f"Stage 1 [YOLOv8]: {len(det_out.detections)} Person(s) Detected"
        hud_stage2 = f"Stage 2 [DeepSORT]: {len(track_out.confirmed_tracks)} Active Track(s) ID: {[t.track_id for t in track_out.confirmed_tracks]}"
        
        # Summarize Stage 3 matching status
        matches = sum(1 for r in face_results if r["face_detected"] and r["face_score"] >= 0.40)
        unmatched = sum(1 for r in face_results if r["face_detected"] and r["face_score"] < 0.40)
        hud_stage3 = f"Stage 3 [Face]: {matches} Matched (Green) | {unmatched} Unmatched (Red)"

        # Backdrop for text
        cv2.rectangle(vis, (5, 5), (600, 100), (0, 0, 0), -1)
        cv2.putText(vis, hud_stage1, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(vis, hud_stage2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(vis, hud_stage3, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Stage 3A Integration Test", vis)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
        frame_id += 1

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
