"""
config.py — Multi-Object Tracking Module Configuration
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

All tunable parameters. No logic here — only constants.
"""

import torch as _torch

# ─────────────────────────────────────────────
#  TRACKER SELECTION
# ─────────────────────────────────────────────
TRACKER_BACKEND: str = "bytetrack"     # "bytetrack" | "deepsort"
DEVICE: str = "cuda" if _torch.cuda.is_available() else "cpu"

# ─────────────────────────────────────────────
#  BYTETRACK SETTINGS
# ─────────────────────────────────────────────
BT_TRACK_THRESH: float = 0.50         # High-confidence detection threshold
BT_TRACK_BUFFER: int = 30             # Max frames to keep a lost track alive
BT_MATCH_THRESH: float = 0.80         # IoU match threshold for track linking
BT_FRAME_RATE: int = 30               # Expected input FPS (for buffer scaling)
BT_MIN_BOX_AREA: float = 10.0        # Discard tiny bboxes (noise guard)

# ─────────────────────────────────────────────
#  DEEPSORT SETTINGS
# ─────────────────────────────────────────────
DS_MAX_AGE: int = 30                  # Frames before a lost track is deleted
DS_N_INIT: int = 3                    # Frames before a new track is confirmed
DS_MAX_IOU_DISTANCE: float = 0.70    # Max IoU distance for matching
DS_MAX_COSINE_DISTANCE: float = 0.40 # Re-ID feature distance threshold
DS_NN_BUDGET: int = 100              # Max stored appearance features / track
DS_REID_MODEL: str = "osnet_x0_25"  # Lightweight torchreid re-ID model

# ─────────────────────────────────────────────
#  OCCLUSION HANDLING
# ─────────────────────────────────────────────
MAX_FRAMES_MISSING: int = 30          # Hold track alive for this many frames
REAPP_IOU_THRESHOLD: float = 0.35    # IoU threshold for re-association

# ─────────────────────────────────────────────
#  OUTPUT / LOGGING
# ─────────────────────────────────────────────
LOG_INTERMEDIATE_STATES: bool = True  # Log track state every frame
MIN_TRACK_CONFIDENCE: float = 0.50   # Don't emit tracks below this confidence
