"""
config.py — Person Detection Module Configuration
Surveillance Intelligence Pipeline — Stage 1: Person Detection

All tunable parameters live here. No logic, only configuration.
"""

from pathlib import Path

import torch as _torch  # used only to auto-detect GPU availability

# ─────────────────────────────────────────────
#  MODEL SETTINGS
# ─────────────────────────────────────────────
_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent
_MODEL_CANDIDATES = [
    _PROJECT_ROOT / "multi_object_tracking_module" / "yolov8s.pt",
    _MODULE_DIR / "yolov8s.pt",
    _MODULE_DIR / "yolov8n.pt",
]
MODEL_PATH: str = str(next((path for path in _MODEL_CANDIDATES if path.exists()), _MODEL_CANDIDATES[-1]))

# Auto-select CUDA if available, fall back to CPU gracefully
DEVICE: str = "cuda" if _torch.cuda.is_available() else "cpu"

# FP16 only makes sense on GPU; force False on CPU to avoid runtime errors
HALF_PRECISION: bool = DEVICE != "cpu"

# ─────────────────────────────────────────────
#  DETECTION SETTINGS
# ─────────────────────────────────────────────
PERSON_CLASS_ID: int = 0               # COCO class index for 'person'
CONFIDENCE_THRESHOLD: float = 0.50     # Minimum detection confidence (tunable)
NMS_IOU_THRESHOLD: float = 0.45       # IoU threshold for Non-Max Suppression
MAX_DETECTIONS: int = 100              # Cap on detections per frame

# ─────────────────────────────────────────────
#  TEMPORAL SMOOTHING SETTINGS
# ─────────────────────────────────────────────
SMOOTHING_WINDOW: int = 3              # Frames to average bounding boxes over
MIN_CONSECUTIVE_FRAMES: int = 2        # Frames a bbox must appear before being emitted
IOU_MATCH_THRESHOLD: float = 0.40     # IoU threshold for linking bboxes across frames

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL: str = "INFO"               # "DEBUG" | "INFO" | "WARNING" | "ERROR"
LOG_INTERMEDIATE_STATES: bool = True  # Write per-frame detection state to logger
