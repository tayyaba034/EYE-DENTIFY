from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np


@dataclass
class HeightEstimate:
    track_id: int
    estimated_height_m: float
    confidence: float
    pose_detected: bool = False
    landmarks: Optional[List[dict]] = None

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "height": {
                "estimated_height_m": round(self.estimated_height_m, 3),
                "confidence": round(self.confidence, 4),
                "pose_detected": self.pose_detected,
            },
            "landmarks": self.landmarks or [],
        }


class HeightEstimator:
    """
    ArUco-aware height estimator adapted from the zip prototype.

    The zip version was a standalone multi-person app using:
    - ArUco marker calibration
    - YOLOv8 pose
    - live camera loop

    This adapted version keeps the same ideas but fits the current pipeline:
    - consumes tracked persons
    - returns per-track structured outputs
    - falls back gracefully when marker or pose model is unavailable
    """

    def __init__(
        self,
        marker_size_cm: float = 10.0,
        assumed_min_height_m: float = 1.45,
        assumed_max_height_m: float = 2.0,
    ) -> None:
        self.marker_size_cm = marker_size_cm
        self.assumed_min_height_m = assumed_min_height_m
        self.assumed_max_height_m = assumed_max_height_m
        self.correction_factor = 1.05
        self.pixels_per_cm: Optional[float] = None
        self.pose_model = self._init_pose_model()
        self._landmarker = self._init_landmarker()
        self._aruco_ready = hasattr(cv2, "aruco")
        if self._aruco_ready:
            self.aruco_dicts = [
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50),
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250),
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50),
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_ARUCO_ORIGINAL),
            ]
            self.aruco_params = cv2.aruco.DetectorParameters()
            self.detectors = [cv2.aruco.ArucoDetector(d, self.aruco_params) for d in self.aruco_dicts]
        else:
            self.aruco_dicts = []
            self.detectors = []

    @staticmethod
    def _default_pose_model_path() -> Path:
        return Path(__file__).resolve().parent / "yolov8n-pose.pt"

    def _init_pose_model(self):
        model_path = self._default_pose_model_path()
        if not model_path.exists():
            return None
        try:
            from ultralytics import YOLO  # type: ignore

            return YOLO(str(model_path))
        except Exception:
            return None

    def _init_landmarker(self):
        model_path = Path(__file__).resolve().parent / "models" / "pose_landmarker.task"
        if not model_path.exists():
            return None
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision

            base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_poses=4,
                min_pose_detection_confidence=0.45,
                min_pose_presence_confidence=0.45,
                min_tracking_confidence=0.45,
            )
            return vision.PoseLandmarker.create_from_options(options)
        except Exception:
            return None

    def _calculate_scale_from_aruco(self, frame: np.ndarray) -> Optional[float]:
        if not self._aruco_ready:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for detector in self.detectors:
            corners, ids, _ = detector.detectMarkers(gray)
            if ids is not None and len(ids) > 0:
                pts = corners[0][0]
                perim = cv2.arcLength(pts, True)
                avg_side_pixels = perim / 4.0
                return avg_side_pixels / self.marker_size_cm
        return None

    def _fallback_height(self, track, frame_height: int) -> HeightEstimate:
        _, _, _, h = [int(v) for v in track.bbox]
        ratio = max(0.0, min(1.0, float(h) / max(1, frame_height)))
        estimated = self.assumed_min_height_m + (
            self.assumed_max_height_m - self.assumed_min_height_m
        ) * ratio
        return HeightEstimate(
            track_id=track.track_id,
            estimated_height_m=estimated,
            confidence=min(0.35, max(0.15, ratio * 0.5)),
            pose_detected=False,
            landmarks=[],
        )

    def _pose_height_from_crop(
        self,
        crop: np.ndarray,
        x1: int,
        y1: int,
    ) -> tuple[Optional[float], List[dict], float]:
        if self.pose_model is None:
            return None, [], 0.0

        try:
            result = self.pose_model(crop, verbose=False)[0]
        except Exception:
            return None, [], 0.0

        if result.keypoints is None or not getattr(result.keypoints, "has_visible", False):
            return None, [], 0.0

        try:
            kpts = result.keypoints.xy.cpu().numpy()
            confs = result.keypoints.conf.cpu().numpy()
        except Exception:
            return None, [], 0.0

        if len(kpts) == 0:
            return None, [], 0.0

        person_kpts = kpts[0]
        person_confs = confs[0] if confs is not None else np.ones(len(person_kpts), dtype=float)

        nose = person_kpts[0]
        left_ank = person_kpts[15]
        right_ank = person_kpts[16]

        if person_confs[0] <= 0.5 or (person_confs[15] <= 0.5 and person_confs[16] <= 0.5):
            return None, [], 0.0

        ankle_y_vals = []
        if person_confs[15] > 0.5:
            ankle_y_vals.append(left_ank[1])
        if person_confs[16] > 0.5:
            ankle_y_vals.append(right_ank[1])
        if not ankle_y_vals:
            return None, [], 0.0

        feet_y = max(ankle_y_vals)
        head_y = float(nose[1])
        pixel_height = float(feet_y - head_y)
        if pixel_height <= 0:
            return None, [], 0.0

        selected_landmarks = []
        visible_count = 0
        yolo_to_mp = {
            0: 0, 1: 2, 2: 5, 3: 7, 4: 8, 5: 11, 6: 12, 7: 13, 8: 14,
            9: 15, 10: 16, 11: 23, 12: 24, 13: 25, 14: 26, 15: 27, 16: 28
        }
        for idx, point in enumerate(person_kpts):
            visibility = float(person_confs[idx]) if idx < len(person_confs) else 0.0
            if visibility > 0.25:
                visible_count += 1
            mp_idx = yolo_to_mp.get(idx, idx)
            selected_landmarks.append(
                {
                    "id": int(mp_idx),
                    "x": int(x1 + point[0]),
                    "y": int(y1 + point[1]),
                    "visibility": round(visibility, 4),
                }
            )

        confidence = min(0.9, max(0.2, visible_count / max(1, len(person_kpts))))
        return pixel_height, selected_landmarks, confidence

    def _pose_height_from_landmarker(
        self,
        crop: np.ndarray,
        x1: int,
        y1: int,
    ) -> tuple[Optional[float], List[dict], float]:
        if self._landmarker is None:
            return None, [], 0.0
        try:
            import mediapipe as mp

            timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB),
            )
            pose_result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception:
            return None, [], 0.0

        if pose_result is None or not pose_result.pose_landmarks:
            return None, [], 0.0

        landmarks = pose_result.pose_landmarks[0]
        selected_landmarks = []
        y_values = []
        visible_count = 0

        for idx, landmark in enumerate(landmarks):
            visibility = float(getattr(landmark, "visibility", 0.0))
            px = int(x1 + landmark.x * crop.shape[1])
            py = int(y1 + landmark.y * crop.shape[0])
            selected_landmarks.append(
                {
                    "id": int(idx),
                    "x": px,
                    "y": py,
                    "visibility": round(visibility, 4),
                }
            )
            if visibility >= 0.4:
                visible_count += 1
                y_values.append(py)

        if len(y_values) < 2:
            return None, [], 0.0

        pixel_height = float(max(y_values) - min(y_values))
        if pixel_height <= 0:
            return None, [], 0.0

        confidence = min(0.85, max(0.2, visible_count / max(1, len(selected_landmarks))))
        return pixel_height, selected_landmarks, confidence

    def process(self, tracking_output, frame) -> List[HeightEstimate]:
        results: List[HeightEstimate] = []
        tracks = getattr(tracking_output, "tracks", tracking_output.confirmed_tracks)
        frame_height = max(1, int(frame.shape[0]))
        frame_width = max(1, int(frame.shape[1]))

        current_scale = self._calculate_scale_from_aruco(frame)
        if current_scale is not None:
            self.pixels_per_cm = current_scale

        for track in tracks:
            if getattr(track, "state", "confirmed") == "lost":
                continue

            x, y, w, h = [int(v) for v in track.bbox]
            
            # --- PADDED & ASPECT-RATIO PRESERVING CROP ---
            # MediaPipe Pose expects standard human aspect ratios. Squeezing it inside tight
            # person boxes warps the landmarks. We expand the crop box symmetrically by 20%
            # to capture the full body, head, and feet naturally.
            pad_w = int(w * 0.20)
            pad_h = int(h * 0.20)
            cx1 = max(0, x - pad_w)
            cy1 = max(0, y - pad_h)
            cx2 = min(frame_width, x + w + pad_w)
            cy2 = min(frame_height, y + h + pad_h)

            crop_w = cx2 - cx1
            crop_h = cy2 - cy1

            pixel_height = None
            landmarks = []
            pose_conf = 0.0

            # Run MediaPipe Pose on each tracked person's crop for multi-person support!
            if crop_w >= 40 and crop_h >= 60 and self._landmarker is not None:
                person_crop = frame[cy1:cy2, cx1:cx2]
                if person_crop.size > 0:
                    try:
                        import mediapipe as mp
                        timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB),
                        )
                        pose_result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
                        
                        if pose_result and pose_result.pose_landmarks and len(pose_result.pose_landmarks) > 0:
                            # Use the best pose (single cropped person)
                            pose = pose_result.pose_landmarks[0]
                            
                            y_values = []
                            visible_count = 0
                            
                            for idx, lm in enumerate(pose):
                                # Map back to full-frame coordinates perfectly!
                                px = int(cx1 + lm.x * crop_w)
                                py = int(cy1 + lm.y * crop_h)
                                visibility = float(getattr(lm, "visibility", 0.0))
                                
                                landmarks.append({
                                    "id": int(idx),
                                    "x": px,
                                    "y": py,
                                    "visibility": round(visibility, 4),
                                })
                                
                                # Gather vertical span of visible body points (shoulders to feet)
                                if visibility >= 0.4:
                                    visible_count += 1
                                    y_values.append(py)
                                    
                            if len(y_values) >= 2:
                                pixel_height = float(max(y_values) - min(y_values))
                                pose_conf = min(0.85, max(0.2, visible_count / max(1, len(pose))))
                    except Exception:
                        pass

            # Fall back to YOLOv8-pose crop if MediaPipe failed
            if pixel_height is None:
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(frame_width, x + w), min(frame_height, y + h)
                crop = frame[y1:y2, x1:x2]
                if crop.size > 0 and x2 - x1 >= 40 and y2 - y1 >= 80:
                    pixel_height, landmarks, pose_conf = self._pose_height_from_crop(crop, x1, y1)

            # Fall back to bounding box height ratio
            if pixel_height is None:
                results.append(self._fallback_height(track, frame_height))
                continue

            if self.pixels_per_cm is not None:
                real_height_cm = (pixel_height / self.pixels_per_cm) * self.correction_factor
                estimated_m = max(0.5, min(2.5, real_height_cm / 100.0))
                confidence = min(0.95, max(0.35, pose_conf))
            else:
                ratio = max(0.0, min(1.0, pixel_height / frame_height))
                estimated_m = self.assumed_min_height_m + (
                    self.assumed_max_height_m - self.assumed_min_height_m
                ) * ratio
                confidence = min(0.75, max(0.25, pose_conf * 0.8))

            results.append(
                HeightEstimate(
                    track_id=track.track_id,
                    estimated_height_m=estimated_m,
                    confidence=confidence,
                    pose_detected=True,
                    landmarks=landmarks,
                )
            )

        return results

    def close(self) -> None:
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        self.pose_model = None

    def __del__(self) -> None:
        self.close()
