from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import os
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class ClothingFeature:
    track_id: int
    color: str
    confidence: float
    detected: bool
    region_bbox: Optional[List[int]] = None
    target_color: Optional[str] = None
    target_match: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "clothing": {
                "color": self.color,
                "confidence": round(float(self.confidence), 4),
                "detected": self.detected,
                "target_color": self.target_color,
                "target_match": self.target_match,
            },
            "region_bbox": self.region_bbox,
        }


class ClothingFeatureExtractor:
    """
    Multi-person clothing color extractor adapted from the original dress-color
    prototype, but integrated into the tracked pipeline.
    """

    def __init__(self, target_color: Optional[str] = None, history_len: int = 15) -> None:
        if target_color is None:
            target_color = os.getenv("CLOTHING_TARGET_COLOR")
        self.target_color = self._normalize_color_name(target_color) if target_color else None
        self.history_len = history_len
        self.color_history: Dict[int, Deque[str]] = {}

        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(haar_path)
        self.use_face_anchor = not self.face_cascade.empty()

        self.colors_bgr = {
            "red": (0, 0, 255),
            "green": (0, 128, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "orange": (0, 165, 255),
            "purple": (128, 0, 128),
            "pink": (203, 192, 255),
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "grey": (128, 128, 128),
            "cyan": (255, 255, 0),
            "maroon": (0, 0, 128),
            "navy": (128, 0, 0),
        }
        self.colors_lab = {
            name: cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2LAB)[0][0]
            for name, bgr in self.colors_bgr.items()
        }

    @staticmethod
    def _normalize_color_name(color: Optional[str]) -> Optional[str]:
        if not color:
            return None
        color = color.strip().lower()
        aliases = {"gray": "grey"}
        return aliases.get(color, color)

    def _get_history(self, track_id: int) -> Deque[str]:
        history = self.color_history.get(track_id)
        if history is None:
            history = deque(maxlen=self.history_len)
            self.color_history[track_id] = history
        return history

    def _smooth_prediction(self, track_id: int, color: str) -> str:
        history = self._get_history(track_id)
        history.append(color)
        return Counter(history).most_common(1)[0][0]

    def _apply_white_balance(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        avg_a = np.mean(lab[:, :, 1])
        avg_b = np.mean(lab[:, :, 2])
        lab[:, :, 1] -= (avg_a - 128)
        lab[:, :, 2] -= (avg_b - 128)
        lab[:, :, 1] = np.clip(lab[:, :, 1], 0, 255)
        lab[:, :, 2] = np.clip(lab[:, :, 2], 0, 255)
        return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)

    def _get_torso_roi(
        self,
        frame: np.ndarray,
        px1: int,
        py1: int,
        px2: int,
        py2: int,
    ) -> Tuple[Optional[np.ndarray], Optional[List[int]]]:
        person = frame[py1:py2, px1:px2]
        if person.size == 0:
            return None, None

        h, w, _ = person.shape
        if h <= 0 or w <= 0:
            return None, None

        # Highly optimized aspect-ratio aware geometric torso region estimation
        y1, y2 = int(0.20 * h), int(0.55 * h)
        x1, x2 = int(0.15 * w), int(0.85 * w)

        roi = person[y1:y2, x1:x2]
        if roi.size == 0:
            return None, None
        return roi, [px1 + x1, py1 + y1, x2 - x1, y2 - y1]

    def _classify_color(self, roi: np.ndarray) -> Tuple[str, float]:
        if np.mean(roi) < 40:
            return "black", 0.95

        roi = cv2.resize(roi, (64, 64))
        balanced_roi = self._apply_white_balance(roi)
        center_roi = roi[16:48, 16:48]
        balanced_center_roi = balanced_roi[16:48, 16:48]
        hsv = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)
        mean_h = float(np.mean(hsv[:, :, 0]))
        mean_s = float(np.mean(hsv[:, :, 1]))
        mean_v = float(np.mean(hsv[:, :, 2]))

        if mean_v < 45:
            return "black", 0.95
        if mean_s < 25 and mean_v > 200:
            return "white", 0.9
        if mean_s < 35:
            return "grey", 0.82

        candidates = []
        for source_roi in (center_roi, balanced_center_roi):
            mean_bgr = np.uint8([[np.mean(source_roi.reshape(-1, 3), axis=0)]])
            target_lab = cv2.cvtColor(mean_bgr, cv2.COLOR_BGR2LAB)[0][0]

            best_color = "unknown"
            min_dist = float("inf")
            second_min_dist = float("inf")
            for name, lab in self.colors_lab.items():
                dist = float(np.linalg.norm(target_lab - lab))
                if dist < min_dist:
                    second_min_dist = min_dist
                    min_dist = dist
                    best_color = name
                elif dist < second_min_dist:
                    second_min_dist = dist
            candidates.append((best_color, min_dist, second_min_dist))

        best_color, min_dist, second_min_dist = min(candidates, key=lambda item: item[1])
        margin = max(0.0, second_min_dist - min_dist) if second_min_dist < float("inf") else 20.0
        confidence = max(0.3, min(0.98, 1.0 - (min_dist / 120.0) + (margin / 200.0)))
        return best_color.lower(), confidence

    def process(self, tracking_output, frame: np.ndarray) -> List[ClothingFeature]:
        results: List[ClothingFeature] = []
        tracks = getattr(tracking_output, "confirmed_tracks", [])

        for track in tracks:
            x, y, w, h = [int(v) for v in track.bbox]
            px1, py1 = max(0, x), max(0, y)
            px2, py2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)

            if px2 - px1 < 30 or py2 - py1 < 60:
                results.append(
                    ClothingFeature(
                        track_id=track.track_id,
                        color="unknown",
                        confidence=0.0,
                        detected=False,
                        region_bbox=None,
                        target_color=self.target_color,
                        target_match=False if self.target_color else None,
                    )
                )
                continue

            roi, region_bbox = self._get_torso_roi(frame, px1, py1, px2, py2)
            if roi is None or region_bbox is None:
                results.append(
                    ClothingFeature(
                        track_id=track.track_id,
                        color="unknown",
                        confidence=0.0,
                        detected=False,
                        region_bbox=None,
                        target_color=self.target_color,
                        target_match=False if self.target_color else None,
                    )
                )
                continue

            color, confidence = self._classify_color(roi)
            smoothed_color = self._smooth_prediction(track.track_id, color)
            target_match = (
                smoothed_color == self.target_color if self.target_color is not None else None
            )
            results.append(
                ClothingFeature(
                    track_id=track.track_id,
                    color=smoothed_color,
                    confidence=confidence,
                    detected=True,
                    region_bbox=region_bbox,
                    target_color=self.target_color,
                    target_match=target_match,
                )
            )

        active_ids = {track.track_id for track in tracks}
        stale_ids = [track_id for track_id in self.color_history if track_id not in active_ids]
        for track_id in stale_ids:
            self.color_history.pop(track_id, None)

        return results
