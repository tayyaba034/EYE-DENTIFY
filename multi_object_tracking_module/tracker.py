"""
tracker.py — Multi-Object Tracker Orchestrator
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

Responsibilities
----------------
* Accept FrameDetectionOutput from Stage 1 (Person Detection).
* Route to the configured tracker backend (ByteTrack or DeepSORT).
* Assign and maintain persistent track_ids across frames.
* Handle occlusion, re-appearance, and clean entry/exit of individuals.
* Emit FrameTrackingOutput consumed by Stage 3 (Feature Extraction).

STRICT CONSTRAINTS (enforced in code):
  - No identity recognition (face / clothing)
  - No decision-making
  - No merging of distinct identities
  - track_id is purely a continuity token — not an identity label
"""

from __future__ import annotations
import logging
import sys
from typing import Optional, List

import numpy as np

from multi_object_tracking_module.config import (
    TRACKER_BACKEND,
    MIN_TRACK_CONFIDENCE,
    LOG_INTERMEDIATE_STATES,
)
from multi_object_tracking_module.schemas import FrameTrackingOutput, TrackedPerson

# Lazy imports of adapters to avoid import-time dependency errors
_bytetrack_adapter = None
_deepsort_adapter  = None

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  MultiObjectTracker
# ─────────────────────────────────────────────────────────────────────────────

class MultiObjectTracker:
    """
    Backend-agnostic multi-object tracker for the surveillance pipeline.

    Accepts detections from Stage 1 and returns persistent track_ids.

    Parameters
    ----------
    backend        : "bytetrack" (default) | "deepsort"
    conf_threshold : Minimum confidence for a track to be emitted.
    """

    def __init__(
        self,
        backend: str = TRACKER_BACKEND,
        conf_threshold: float = MIN_TRACK_CONFIDENCE,
    ) -> None:
        self._backend = backend.lower()
        self._conf_threshold = conf_threshold
        self._tracker = self._load_backend(self._backend)
        logger.info(
            "MultiObjectTracker initialised | backend=%s conf_threshold=%.2f",
            backend, conf_threshold,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        detection_output,           # FrameDetectionOutput from Stage 1
        frame: Optional[np.ndarray] = None,  # required for DeepSORT (re-ID)
    ) -> FrameTrackingOutput:
        """
        Process one frame of detections and return tracked persons.

        Parameters
        ----------
        detection_output : FrameDetectionOutput from person_detection_module.
        frame            : Raw BGR numpy frame (DeepSORT only). Pass None for
                           ByteTrack (IoU-only) mode.

        Returns
        -------
        FrameTrackingOutput
            All tracks for this frame. Use .confirmed_tracks to get only
            stable tracks safe for downstream processing.
        """
        frame_id = detection_output.frame_id

        # ── Build (bbox, confidence) tuples ──────────────────────────────────
        dets = [
            (d.bbox, d.confidence)
            for d in detection_output.detections
            if d.confidence >= self._conf_threshold
        ]

        # ── Run tracker backend ───────────────────────────────────────────────
        if self._backend == "bytetrack":
            raw_tracks: List[TrackedPerson] = self._tracker.update(
                dets, frame_id
            )
        elif self._backend == "deepsort":
            if frame is None:
                logger.warning(
                    "DeepSORT requires a raw frame for re-ID; "
                    "tracking quality will degrade."
                )
                frame = np.zeros((1, 1, 3), dtype=np.uint8)
            raw_tracks = self._tracker.update(dets, frame, frame_id)
        else:
            raise ValueError(f"Unknown tracker backend: {self._backend}")

        # ── Build output ──────────────────────────────────────────────────────
        output = FrameTrackingOutput(
            frame_id=frame_id,
            tracks=raw_tracks,
        )

        if LOG_INTERMEDIATE_STATES:
            logger.info(
                "frame_id=%d | detections=%d | tracks=%d | confirmed=%d",
                frame_id,
                len(dets),
                output.count,
                len(output.confirmed_tracks),
            )

        return output

    def reset_stream(self) -> None:
        """
        Reset tracker state.
        Call when switching video streams or after a scene cut.
        """
        self._tracker.reset()
        logger.info("MultiObjectTracker stream state reset.")

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_backend(self, backend: str):
        if backend == "bytetrack":
            from multi_object_tracking_module.bytetrack_adapter import ByteTrackAdapter
            return ByteTrackAdapter()
        elif backend == "deepsort":
            from multi_object_tracking_module.deepsort_adapter import DeepSORTAdapter
            return DeepSORTAdapter()
        else:
            raise ValueError(
                f"Unknown tracker backend '{backend}'. "
                "Choose 'bytetrack' or 'deepsort'."
            )
