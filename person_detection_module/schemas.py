"""
schemas.py — Structured Output Schemas
Surveillance Intelligence Pipeline — Stage 1: Person Detection

Defines the canonical JSON-serialisable output contract for this module.
All downstream stages (tracking, feature extraction) must consume this format.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List
import json


# ─────────────────────────────────────────────────────────────────────────────
#  Core detection unit
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """
    A single detected person bounding box in one frame.

    Fields
    ------
    bbox       : [x, y, width, height] — top-left corner + dimensions (pixels)
    confidence : float in [0.0, 1.0] — raw model confidence after NMS
    """
    bbox: List[float]        # [x, y, w, h]
    confidence: float        # e.g. 0.87

    def to_dict(self) -> dict:
        return {
            "bbox": [round(v, 2) for v in self.bbox],
            "confidence": round(self.confidence, 4),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Frame-level output (matches pipeline spec exactly)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FrameDetectionOutput:
    """
    Complete per-frame detection output consumed by the tracking stage.

    Matches the spec:
    {
      "frame_id": int,
      "detections": [
        {"bbox": [x, y, width, height], "confidence": float}
      ]
    }

    An empty 'detections' list is valid — it means no persons were found.
    """
    frame_id: int
    detections: List[DetectionResult] = field(default_factory=list)

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a plain dict (JSON-serialisable)."""
        return {
            "frame_id": self.frame_id,
            "detections": [d.to_dict() for d in self.detections],
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    # ── Convenience ────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Number of detected persons in this frame."""
        return len(self.detections)

    @property
    def is_empty(self) -> bool:
        """True when no persons were detected."""
        return self.count == 0

    def __repr__(self) -> str:
        return (
            f"FrameDetectionOutput(frame_id={self.frame_id}, "
            f"persons={self.count})"
        )
