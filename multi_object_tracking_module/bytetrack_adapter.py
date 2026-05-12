"""
bytetrack_adapter.py — ByteTrack Adapter
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

Wraps the ByteTrack algorithm (via ultralytics built-in tracker or
a standalone implementation) exposing a clean update() interface.

ByteTrack Strategy
------------------
* High-confidence detections (≥ BT_TRACK_THRESH) form primary matches.
* Low-confidence detections are used as a safety net for lost tracks.
* Kalman filter predicts positions during missed frames.
* IoU-based matching — no appearance features needed.
"""

from __future__ import annotations
import logging
import numpy as np
from typing import List, Tuple

from multi_object_tracking_module.config import (
    BT_TRACK_THRESH,
    BT_TRACK_BUFFER,
    BT_MATCH_THRESH,
    BT_FRAME_RATE,
    BT_MIN_BOX_AREA,
    MAX_FRAMES_MISSING,
)
from multi_object_tracking_module.schemas import TrackedPerson

logger = logging.getLogger(__name__)

# ─── track states ─────────────────────────────────────────────────────────────
_STATE_TENTATIVE = "tentative"
_STATE_CONFIRMED = "confirmed"
_STATE_LOST      = "lost"


class _KalmanTrack:
    """
    Single track managed by a simple Kalman-like state model.
    Stores bbox, velocity, age, consecutive misses.
    """
    _id_counter = 0

    def __init__(self, bbox: List[float], confidence: float) -> None:
        _KalmanTrack._id_counter += 1
        self.track_id   = _KalmanTrack._id_counter
        self.bbox       = list(bbox)         # [x, y, w, h]
        self._velocity  = [0.0, 0.0, 0.0, 0.0]
        self.confidence = confidence
        self.frames_seen = 1
        self.missed      = 0
        self.state       = _STATE_TENTATIVE

    def predict(self) -> None:
        """Move bbox forward by last known velocity."""
        self.bbox = [b + v for b, v in zip(self.bbox, self._velocity)]

    def update(self, bbox: List[float], confidence: float) -> None:
        """Update position and velocity from a matched detection."""
        alpha = 0.7
        new_vel = [alpha * (n - o) + (1 - alpha) * v
                   for n, o, v in zip(bbox, self.bbox, self._velocity)]
        self._velocity  = new_vel
        self.bbox       = list(bbox)
        self.confidence = confidence
        self.frames_seen += 1
        self.missed = 0
        if self.frames_seen >= 3:
            self.state = _STATE_CONFIRMED

    def mark_missed(self) -> None:
        self.missed += 1
        if self.missed > MAX_FRAMES_MISSING:
            self.state = _STATE_LOST
        elif self.state == _STATE_CONFIRMED:
            self.state = _STATE_LOST


def _iou(a: List[float], b: List[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    xi1, yi1 = max(ax, bx), max(ay, by)
    xi2, yi2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0.0, xi2 - xi1) * max(0.0, yi2 - yi1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


class ByteTrackAdapter:
    """
    Lightweight ByteTrack-style multi-object tracker.

    Usage
    -----
    tracker = ByteTrackAdapter()
    tracked = tracker.update(detections, frame_id)
    """

    def __init__(self) -> None:
        self._tracks: List[_KalmanTrack] = []

    def update(
        self,
        detections: List[Tuple[List[float], float]],  # [(bbox, conf), ...]
        frame_id: int,
    ) -> List[TrackedPerson]:
        """
        Update tracks with new frame detections.

        Parameters
        ----------
        detections : list of (bbox, confidence) from Stage 1.
        frame_id   : current frame index.

        Returns
        -------
        List of TrackedPerson (all states — caller filters for "confirmed").
        """
        # ── Filter tiny boxes ───────────────────────────────────────────────
        detections = [
            (b, c) for b, c in detections
            if b[2] * b[3] >= BT_MIN_BOX_AREA
        ]

        # ── Predict all tracks forward ───────────────────────────────────────
        for t in self._tracks:
            t.predict()

        # ── Split detections: high vs low confidence ─────────────────────────
        high = [(b, c) for b, c in detections if c >= BT_TRACK_THRESH]
        low  = [(b, c) for b, c in detections if c <  BT_TRACK_THRESH]

        matched_track_ids: set[int] = set()
        matched_det_indices: set[int] = set()
        new_track_ids: set[int] = set()

        # ── Pass 1: match high-confidence dets → all tracks ──────────────────
        active = [t for t in self._tracks if t.state != _STATE_LOST]
        for d_i, (bbox, conf) in enumerate(high):
            best_t, best_iou = None, 1.0 - BT_MATCH_THRESH
            for t in active:
                if t.track_id in matched_track_ids:
                    continue
                dist = 1.0 - _iou(bbox, t.bbox)
                if dist < best_iou:
                    best_iou = dist
                    best_t = t
            if best_t is not None:
                best_t.update(bbox, conf)
                matched_track_ids.add(best_t.track_id)
                matched_det_indices.add(d_i)

        # ── Pass 2: match low-confidence dets → lost tracks ──────────────────
        lost_tracks = [t for t in self._tracks if t.state == _STATE_LOST]
        for d_i, (bbox, conf) in enumerate(low):
            best_t, best_iou = None, 1.0 - BT_MATCH_THRESH
            for t in lost_tracks:
                if t.track_id in matched_track_ids:
                    continue
                dist = 1.0 - _iou(bbox, t.bbox)
                if dist < best_iou:
                    best_iou = dist
                    best_t = t
            if best_t is not None:
                best_t.update(bbox, conf)
                matched_track_ids.add(best_t.track_id)

        # ── Unmatched high-confidence dets → new tracks ───────────────────────
        for d_i, (bbox, conf) in enumerate(high):
            if d_i not in matched_det_indices:
                track = _KalmanTrack(bbox, conf)
                self._tracks.append(track)
                new_track_ids.add(track.track_id)

        # ── Mark unmatched tracks missed ──────────────────────────────────────
        for t in self._tracks:
            if t.track_id not in matched_track_ids and t.track_id not in new_track_ids:
                t.mark_missed()

        # ── Prune dead tracks ─────────────────────────────────────────────────
        self._tracks = [
            t for t in self._tracks if t.state != _STATE_LOST
            or t.missed <= MAX_FRAMES_MISSING
        ]

        # ── Build output ──────────────────────────────────────────────────────
        result = [
            TrackedPerson(
                track_id=t.track_id,
                bbox=t.bbox,
                confidence=t.confidence,
                state=t.state,
                frames_seen=t.frames_seen,
            )
            for t in self._tracks
        ]
        logger.debug(
            "ByteTrack frame=%d | dets=%d tracks=%d confirmed=%d",
            frame_id, len(detections), len(result),
            sum(1 for r in result if r.state == _STATE_CONFIRMED),
        )
        return result

    def reset(self) -> None:
        self._tracks.clear()
        _KalmanTrack._id_counter = 0
