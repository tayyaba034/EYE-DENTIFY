"""
schemas.py — Structured Output Schemas
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

Defines the canonical output contract for this module.
Stage 3 (Feature Extraction) must consume this format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import json


@dataclass
class TrackedPerson:
    """
    One tracked person in a single frame.

    Fields
    ------
    track_id    : Persistent integer ID across frames.
    bbox        : [x, y, width, height] in pixels.
    confidence  : Detection confidence from Stage 1.
    state       : "confirmed" | "tentative" | "lost"
    frames_seen : Consecutive frames this track has been observed.
    """
    track_id: int
    bbox: List[float]
    confidence: float
    state: str          # "confirmed" | "tentative" | "lost"
    frames_seen: int = 1

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "bbox": [round(v, 2) for v in self.bbox],
            "confidence": round(self.confidence, 4),
            "state": self.state,
            "frames_seen": self.frames_seen,
        }


@dataclass
class FrameTrackingOutput:
    """
    Per-frame tracking output consumed by Feature Extraction (Stage 3).

    Schema
    ------
    {
      "frame_id": int,
      "tracks": [
        {
          "track_id": int,
          "bbox": [x, y, width, height],
          "confidence": float,
          "state": "confirmed" | "tentative" | "lost",
          "frames_seen": int
        }
      ]
    }
    """
    frame_id: int
    tracks: List[TrackedPerson] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "tracks": [t.to_dict() for t in self.tracks],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @property
    def confirmed_tracks(self) -> List[TrackedPerson]:
        """Only confirmed tracks — safe to pass to Feature Extraction."""
        return [t for t in self.tracks if t.state == "confirmed"]

    @property
    def active_ids(self) -> List[int]:
        return [t.track_id for t in self.tracks]

    @property
    def count(self) -> int:
        return len(self.tracks)

    @property
    def is_empty(self) -> bool:
        return self.count == 0

    def __repr__(self) -> str:
        return (
            f"FrameTrackingOutput(frame_id={self.frame_id}, "
            f"total={self.count}, confirmed={len(self.confirmed_tracks)})"
        )
