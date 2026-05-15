"""
run_detection.py — Person Detection Test Runner
Surveillance Intelligence Pipeline — Stage 1: Person Detection

Usage
-----
# Webcam (default)
python run_detection.py

# Video file
python run_detection.py --source path/to/video.mp4

# Single image
python run_detection.py --source path/to/image.jpg --image

# Disable temporal smoothing
python run_detection.py --no-smooth

# Custom confidence threshold
python run_detection.py --conf 0.4

Controls (live window)
------
  q  : Quit
  r  : Reset temporal smoother state
"""

import sys
import os
import argparse
import logging

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ── Make sure package imports work whether run from the repo root or module dir
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PARENT = os.path.dirname(MODULE_DIR)
if PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, PACKAGE_PARENT)

import cv2
import numpy as np

from person_detection_module.detector import PersonDetector
from person_detection_module.config import MODEL_PATH
from person_detection_module.schemas import FrameDetectionOutput

# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_detection")


# ─────────────────────────────────────────────────────────────────────────────
#  Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _draw(frame: np.ndarray, output: FrameDetectionOutput) -> np.ndarray:
    """Overlay bounding boxes and confidence scores on the frame."""
    vis = frame.copy()
    for det in output.detections:
        x, y, w, h = [int(v) for v in det.bbox]
        conf = det.confidence
        color = (0, 220, 50)   # green

        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        label = f"person {conf:.2f}"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (x, y - lh - 6), (x + lw + 4, y), color, -1)
        cv2.putText(
            vis, label,
            (x + 2, y - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            (0, 0, 0), 1, cv2.LINE_AA,
        )

    # HUD
    hud = (
        f"frame={output.frame_id} | "
        f"persons={output.count} | "
        f"press Q to quit"
    )
    cv2.putText(vis, hud, (10, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 100), 2, cv2.LINE_AA)
    return vis


# ─────────────────────────────────────────────────────────────────────────────
#  Single-image mode
# ─────────────────────────────────────────────────────────────────────────────

def run_image(detector: PersonDetector, source: str) -> None:
    frame = cv2.imread(source)
    if frame is None:
        logger.error("Cannot read image: %s", source)
        sys.exit(1)

    output = detector.detect(frame, frame_id=0)
    logger.info("Result:\n%s", output.to_json())

    vis = _draw(frame, output)
    cv2.imshow("Person Detection — Stage 1", vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# ─────────────────────────────────────────────────────────────────────────────
#  Video / webcam mode
# ─────────────────────────────────────────────────────────────────────────────

def run_video(detector: PersonDetector, source) -> None:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error("Cannot open source: %s", source)
        sys.exit(1)

    logger.info(
        "Stream opened | resolution=%dx%d  fps=%.1f",
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        cap.get(cv2.CAP_PROP_FPS),
    )

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.info("Stream ended or no frame — exiting.")
            break

        output = detector.detect(frame, frame_id)

        # Pretty-print every 30 frames so the terminal stays readable
        if frame_id % 30 == 0:
            logger.info("JSON output:\n%s", output.to_json())

        vis = _draw(frame, output)
        cv2.imshow("Person Detection — Stage 1", vis)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            logger.info("User quit.")
            break
        elif key == ord("r"):
            detector.reset_stream()
            logger.info("Smoother reset.")

        frame_id += 1

    cap.release()
    cv2.destroyAllWindows()
    logger.info("Total frames processed: %d", frame_id)


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Person Detection — Stage 1")
    p.add_argument("--source",    default="0",    help="Webcam index, video path, or image path")
    p.add_argument("--conf",      type=float, default=0.5,  help="Confidence threshold")
    p.add_argument("--model",     default=MODEL_PATH,       help="YOLOv8 model file")
    p.add_argument("--no-smooth", action="store_true",      help="Disable temporal smoothing")
    p.add_argument("--image",     action="store_true",      help="Treat source as a single image")
    return p.parse_args()


def main():
    args = parse_args()

    # Convert webcam index to int if numeric
    source = int(args.source) if args.source.isdigit() else args.source

    logger.info(
        "Initialising PersonDetector | model=%s conf=%.2f smooth=%s",
        args.model, args.conf, not args.no_smooth,
    )

    detector = PersonDetector(
        model_path=args.model,
        conf_threshold=args.conf,
        enable_smoothing=not args.no_smooth,
    )

    if args.image:
        run_image(detector, str(source))
    else:
        run_video(detector, source)


if __name__ == "__main__":
    main()
