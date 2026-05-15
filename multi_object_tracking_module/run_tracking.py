"""
run_tracking.py — Multi-Object Tracking Test Runner
Surveillance Intelligence Pipeline — Stages 1 & 2

Usage
-----
# Webcam (default)
python run_tracking.py

# Video file
python run_tracking.py --source path/to/video.mp4

Controls (live window)
------
  q  : Quit
  r  : Reset tracking state
"""

import sys
import os
import argparse
import logging

# Workaround for OpenMP Error #15 (multiple libiomp5md.dll initialised)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure modules are importable from parent directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import cv2
import numpy as np

# Stage 1
from person_detection_module.detector import PersonDetector

# Stage 2
from multi_object_tracking_module.tracker import MultiObjectTracker
from multi_object_tracking_module.schemas import FrameTrackingOutput
from multi_object_tracking_module.config import TRACKER_BACKEND

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_tracking")


# ─────────────────────────────────────────────────────────────────────────────
#  Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

# Assign a deterministic color based on track_id
def _get_color(track_id: int) -> tuple[int, int, int]:
    colors = [
        (255, 50, 50), (50, 255, 50), (50, 50, 255), (255, 255, 0),
        (0, 255, 255), (255, 0, 255), (255, 128, 0), (0, 128, 255),
        (128, 0, 255), (255, 0, 128)
    ]
    return colors[track_id % len(colors)]


def _draw(
    frame: np.ndarray,
    tracking_output: FrameTrackingOutput,
    backend: str,
) -> np.ndarray:
    vis = frame.copy()
    
    # Only draw confirmed tracks
    for track in tracking_output.confirmed_tracks:
        x, y, w, h = [int(v) for v in track.bbox]
        tid = track.track_id
        color = _get_color(tid)

        # Bounding box
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        
        # Label
        label = f"ID: {tid}"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(vis, (x, y - lh - 8), (x + lw + 4, y), color, -1)
        cv2.putText(
            vis, label,
            (x + 2, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (255, 255, 255), 2, cv2.LINE_AA,
        )

    # HUD
    confirmed_count = len(tracking_output.confirmed_tracks)
    hud = (
        f"frame={tracking_output.frame_id} | "
        f"tracks={confirmed_count} | "
        f"{backend}"
    )
    cv2.putText(vis, hud, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    return vis


# ─────────────────────────────────────────────────────────────────────────────
#  Video / webcam mode
# ─────────────────────────────────────────────────────────────────────────────

def run_video(
    detector: PersonDetector,
    tracker: MultiObjectTracker,
    source,
    backend: str,
) -> None:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error("Cannot open source: %s", source)
        sys.exit(1)

    logger.info("Stream opened | starting Stages 1 & 2...")

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Stage 1: Detection
        det_out = detector.detect(frame, frame_id)
        
        # Stage 2: Tracking (pass the raw frame for DeepSORT re-ID)
        track_out = tracker.update(det_out, frame=frame)

        if frame_id % 30 == 0:
            logger.info("Tracking Output:\n%s", track_out.to_json())

        vis = _draw(frame, track_out, backend=backend)
        cv2.imshow(f"Multi-Object Tracking ({backend})", vis)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            detector.reset_stream()
            tracker.reset_stream()
            logger.info("State reset.")

        frame_id += 1

    cap.release()
    cv2.destroyAllWindows()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Webcam index or video path")
    parser.add_argument(
        "--backend",
        default=TRACKER_BACKEND,
        choices=["bytetrack", "deepsort"],
        help="Tracking backend to use",
    )
    args = parser.parse_args()
    
    source = int(args.source) if args.source.isdigit() else args.source

    logger.info("Initialising Stage 1 (Detection)...")
    detector = PersonDetector(model_path="yolov8s.pt", conf_threshold=0.5)

    logger.info("Initialising Stage 2 (Tracking) with %s...", args.backend)
    tracker = MultiObjectTracker(backend=args.backend)

    run_video(detector, tracker, source, backend=args.backend)


if __name__ == "__main__":
    main()
