from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

import cv2


def _bbox_iou(box_a: List[float], box_b: List[float]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    a_x2 = ax + aw
    a_y2 = ay + ah
    b_x2 = bx + bw
    b_y2 = by + bh

    inter_x1 = max(ax, bx)
    inter_y1 = max(ay, by)
    inter_x2 = min(a_x2, b_x2)
    inter_y2 = min(a_y2, b_y2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0.0:
        return 0.0

    area_a = max(0.0, aw) * max(0.0, ah)
    area_b = max(0.0, bw) * max(0.0, bh)
    denom = area_a + area_b - inter_area
    if denom <= 0.0:
        return 0.0
    return float(inter_area / denom)


@dataclass
class _CachedFaces:
    timestamp: float
    faces: List[Dict[str, Any]]


class NoOpFaceNode:
    def process(self, tracking_output, frame) -> List[Dict[str, Any]]:
        _ = frame
        return [
            {
                "track_id": track.track_id,
                "face_score": 0.0,
                "face_detected": False,
            }
            for track in tracking_output.confirmed_tracks
        ]


class EdgeFaceDetectionNode:
    """
    Uses ESP32 `/faces` metadata to provide face detection signal without recognition.
    """

    def __init__(self, api_base_url: str, timeout_s: float = 0.25, cache_ttl_s: float = 0.2) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.cache_ttl_s = cache_ttl_s
        self._cache: Optional[_CachedFaces] = None

    def _fetch_faces(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._cache is not None and (now - self._cache.timestamp) < self.cache_ttl_s:
            return self._cache.faces

        endpoint = f"{self.api_base_url}/faces"
        try:
            with urlopen(endpoint, timeout=self.timeout_s) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError):
            data = {}

        raw_faces = data.get("faces", []) if isinstance(data, dict) else []
        faces: List[Dict[str, Any]] = []
        for item in raw_faces:
            if not isinstance(item, dict):
                continue
            bbox = item.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            try:
                x, y, w, h = [float(v) for v in bbox]
            except (TypeError, ValueError):
                continue
            conf = item.get("confidence", 0.7)
            try:
                confidence = float(conf)
            except (TypeError, ValueError):
                confidence = 0.7
            faces.append({"bbox": [x, y, w, h], "confidence": max(0.0, min(1.0, confidence))})

        self._cache = _CachedFaces(timestamp=now, faces=faces)
        return faces

    def process(self, tracking_output, frame) -> List[Dict[str, Any]]:
        _ = frame
        faces = self._fetch_faces()
        results: List[Dict[str, Any]] = []

        for track in tracking_output.confirmed_tracks:
            track_bbox = [float(v) for v in track.bbox]
            best_face = None
            best_iou = 0.0
            for face in faces:
                iou = _bbox_iou(track_bbox, face["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_face = face

            if best_face is not None and best_iou >= 0.03:
                face_conf = float(best_face["confidence"])
                score = max(0.0, min(1.0, 0.65 * face_conf + 0.35 * min(1.0, best_iou / 0.4)))
                results.append(
                    {
                        "track_id": track.track_id,
                        "face_score": score,
                        "face_detected": True,
                        "face_bbox": [int(v) for v in best_face["bbox"]],
                        "edge_face_source": self.api_base_url,
                    }
                )
            else:
                results.append(
                    {
                        "track_id": track.track_id,
                        "face_score": 0.0,
                        "face_detected": False,
                        "edge_face_source": self.api_base_url,
                    }
                )

        return results


class OpenCVFaceDetectionNode:
    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def process(self, tracking_output, frame) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        confirmed_tracks = getattr(tracking_output, "confirmed_tracks", [])

        for track in confirmed_tracks:
            x, y, w, h = [int(v) for v in track.bbox]
            px1, py1 = max(0, x), max(0, y)
            px2, py2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
            crop = frame[py1:py2, px1:px2]

            if crop.size == 0 or self.face_cascade.empty():
                results.append(
                    {
                        "track_id": track.track_id,
                        "face_score": 0.0,
                        "face_detected": False,
                    }
                )
                continue

            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            if len(faces) == 0:
                results.append(
                    {
                        "track_id": track.track_id,
                        "face_score": 0.0,
                        "face_detected": False,
                    }
                )
                continue

            fx, fy, fw, fh = max(faces, key=lambda face: face[2] * face[3])
            abs_bbox = [px1 + fx, py1 + fy, px1 + fx + fw, py1 + fy + fh]
            face_area = float(fw * fh)
            crop_area = max(1.0, float(crop.shape[0] * crop.shape[1]))
            score = max(0.35, min(0.92, 0.55 + 0.45 * (face_area / crop_area)))
            results.append(
                {
                    "track_id": track.track_id,
                    "face_score": score,
                    "face_detected": True,
                    "face_bbox": abs_bbox,
                }
            )

        return results


def build_face_node(mode: str, edge_face_api: Optional[str]):
    mode_normalized = (mode or "recognition").strip().lower()
    if mode_normalized == "none":
        return NoOpFaceNode()
    if mode_normalized == "edge":
        if not edge_face_api:
            raise ValueError("edge face mode requires --edge-face-api (ESP32 base URL)")
        return EdgeFaceDetectionNode(api_base_url=edge_face_api)

    try:
        from facial_recognition_module.src.face_node import FaceExtractorNode

        return FaceExtractorNode()
    except Exception:
        return OpenCVFaceDetectionNode()
