"""
temporal_smoother.py — Temporal Detection Smoother
Surveillance Intelligence Pipeline — Stage 1: Person Detection

Reduces flickering / ephemeral bounding boxes that the raw YOLO model emits.
This is a DETECTION-level smoother only — it does NOT perform identity
tracking (that is handled by DeepSORT/ByteTrack in Stage 2).

Algorithm
---------
1. For every new frame, compute IoU between incoming raw bboxes and the
   tracked candidate set from the previous frame.
2. If IoU ≥ IOU_MATCH_THRESHOLD → update existing candidate (EMA smooth).
3. If no match → create a new candidate (age = 1 frame, not yet emitted).
4. Candidates that have survived ≥ MIN_CONSECUTIVE_FRAMES are emitted.
5. Candidates that have not been matched for SMOOTHING_WINDOW frames are pruned.
"""

from __future__ import annotations
import logging
from typing import List, Tuple
from dataclasses import dataclass, field

from person_detection_module.config import (
    SMOOTHING_WINDOW,
    MIN_CONSECUTIVE_FRAMES,
    IOU_MATCH_THRESHOLD,
)
from person_detection_module.schemas import DetectionResult

logger = logging.getLogger(__name__)

# ─── EMA blend factor for bbox position smoothing ────────────────────────────
_ALPHA = 0.6   # new observation weight (0 = ignore new, 1 = no smoothing)


# ─────────────────────────────────────────────────────────────────────────────
#  Internal candidate state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Candidate:
    """Tracks a potentially flickering detection internally."""
    bbox: List[float]          # [x, y, w, h] — smoothed
    confidence: float
    age: int = 1               # consecutive frames seen
    missed: int = 0            # consecutive frames NOT matched

    def update(self, bbox: List[float], confidence: float) -> None:
        """EMA-blend the new observation into the running estimate."""
        self.bbox = [
            _ALPHA * n + (1 - _ALPHA) * o
            for n, o in zip(bbox, self.bbox)
        ]
        self.confidence = _ALPHA * confidence + (1 - _ALPHA) * self.confidence
        self.age += 1
        self.missed = 0

    def mark_missed(self) -> None:
        self.missed += 1


# ─────────────────────────────────────────────────────────────────────────────
#  Public smoother class
# ─────────────────────────────────────────────────────────────────────────────

class TemporalSmoother:
    """
    Stateful per-stream temporal smoother.

    Usage
    -----
    smoother = TemporalSmoother()
    stable_detections = smoother.update(raw_detections)
    """

    def __init__(self) -> None:
        self._candidates: List[_Candidate] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, raw: List[DetectionResult]) -> List[DetectionResult]:
        """
        Feed one frame's raw detections; return only stable, smoothed ones.

        Parameters
        ----------
        raw : list of DetectionResult
            Fresh detections from YOLO for this frame (after NMS + conf filter).

        Returns
        -------
        list of DetectionResult
            Stable, EMA-smoothed detections ready for downstream tracking.
        """
        matched_candidate_indices: set[int] = set()
        matched_raw_indices: set[int] = set()
        newly_created_candidate_indices: set[int] = set()

        # ── Step 1: match raw → candidates via IoU ─────────────────────────
        iou_matrix = _compute_iou_matrix(
            [r.bbox for r in raw],
            [c.bbox for c in self._candidates],
        )

        for r_idx, row in enumerate(iou_matrix):
            if not row:
                continue
            best_c_idx = max(range(len(row)), key=lambda i: row[i])
            if (
                row[best_c_idx] >= IOU_MATCH_THRESHOLD
                and best_c_idx not in matched_candidate_indices
            ):
                self._candidates[best_c_idx].update(
                    raw[r_idx].bbox, raw[r_idx].confidence
                )
                matched_candidate_indices.add(best_c_idx)
                matched_raw_indices.add(r_idx)

        # ── Step 2: unmatched raw → new candidates ──────────────────────────
        for r_idx, det in enumerate(raw):
            if r_idx not in matched_raw_indices:
                self._candidates.append(_Candidate(bbox=list(det.bbox),
                                                    confidence=det.confidence))
                newly_created_candidate_indices.add(len(self._candidates) - 1)

        # ── Step 3: unmatched candidates → mark missed ──────────────────────
        for c_idx, cand in enumerate(self._candidates):
            if (
                c_idx not in matched_candidate_indices
                and c_idx not in newly_created_candidate_indices
            ):
                cand.mark_missed()

        # ── Step 4: prune stale candidates ──────────────────────────────────
        self._candidates = [
            c for c in self._candidates if c.missed < SMOOTHING_WINDOW
        ]

        # ── Step 5: emit only stable candidates ─────────────────────────────
        stable: List[DetectionResult] = []
        for cand in self._candidates:
            if cand.age >= MIN_CONSECUTIVE_FRAMES:
                stable.append(DetectionResult(
                    bbox=cand.bbox,
                    confidence=cand.confidence,
                ))

        logger.debug(
            "TemporalSmoother: raw=%d candidates=%d stable=%d",
            len(raw), len(self._candidates), len(stable),
        )
        return stable

    def reset(self) -> None:
        """Clear all candidate state (call when switching video stream)."""
        self._candidates.clear()


# ─────────────────────────────────────────────────────────────────────────────
#  IoU helpers
# ─────────────────────────────────────────────────────────────────────────────

def _iou(box_a: List[float], box_b: List[float]) -> float:
    """Compute Intersection-over-Union between two [x, y, w, h] boxes."""
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    xi1 = max(ax, bx)
    yi1 = max(ay, by)
    xi2 = min(ax + aw, bx + bw)
    yi2 = min(ay + ah, by + bh)

    inter_w = max(0.0, xi2 - xi1)
    inter_h = max(0.0, yi2 - yi1)
    inter_area = inter_w * inter_h

    union_area = aw * ah + bw * bh - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def _compute_iou_matrix(
    raw_boxes: List[List[float]],
    candidate_boxes: List[List[float]],
) -> List[List[float]]:
    """Return iou_matrix[r][c] = IoU(raw_boxes[r], candidate_boxes[c])."""
    return [
        [_iou(r, c) for c in candidate_boxes]
        for r in raw_boxes
    ]
