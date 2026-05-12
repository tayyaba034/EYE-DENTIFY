"""
detector.py — Core Person Detection Engine
Surveillance Intelligence Pipeline — Stage 1: Person Detection

Responsibilities
----------------
* Load and manage a YOLOv8 model instance.
* Accept raw video frames (numpy arrays).
* Return ONLY 'person' class detections after NMS + confidence filtering.
* Pass raw detections through TemporalSmoother before emitting.
* Produce FrameDetectionOutput — the canonical output for Stage 2 (Tracking).

STRICT CONSTRAINTS (enforced in code):
  - No identity logic
  - No tracking logic
  - No per-person labelling or classification
  - Empty result on zero detections — never hallucinate
"""

from __future__ import annotations
import logging
import time
from typing import Optional

import numpy as np

from person_detection_module.config import (
    MODEL_PATH,
    DEVICE,
    HALF_PRECISION,
    PERSON_CLASS_ID,
    CONFIDENCE_THRESHOLD,
    NMS_IOU_THRESHOLD,
    MAX_DETECTIONS,
    LOG_INTERMEDIATE_STATES,
)
from person_detection_module.schemas import DetectionResult, FrameDetectionOutput
from person_detection_module.temporal_smoother import TemporalSmoother

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  PersonDetector
# ─────────────────────────────────────────────────────────────────────────────

class PersonDetector:
    """
    YOLOv8-powered person detector for the surveillance pipeline.

    Thread Safety
    -------------
    One instance per video stream is recommended. The internal TemporalSmoother
    holds per-stream state; sharing across streams will corrupt results.

    Parameters
    ----------
    model_path       : Path to YOLOv8 weights (.pt file).
    conf_threshold   : Minimum confidence to retain a detection.
    nms_iou          : IoU threshold used during Non-Max Suppression.
    device           : Inference device — "cuda" | "cpu" | "mps".
    enable_smoothing : Whether to apply temporal smoothing.
    """

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        conf_threshold: float = CONFIDENCE_THRESHOLD,
        nms_iou: float = NMS_IOU_THRESHOLD,
        device: str = DEVICE,
        enable_smoothing: bool = True,
    ) -> None:
        self._conf = conf_threshold
        self._nms_iou = nms_iou
        self._device = device
        self._enable_smoothing = enable_smoothing
        self._smoother = TemporalSmoother()
        self._model = self._load_model(model_path, device)
        logger.info(
            "PersonDetector initialised | model=%s device=%s conf=%.2f",
            model_path, device, conf_threshold,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray, frame_id: int) -> FrameDetectionOutput:
        """
        Run person detection on a single frame.

        Parameters
        ----------
        frame    : BGR numpy array (H × W × 3) from OpenCV / camera feed.
        frame_id : Sequential frame index (used in output schema).

        Returns
        -------
        FrameDetectionOutput
            Structured JSON-serialisable output ready for Stage 2 (Tracking).
            'detections' is an empty list when no persons are found.
        """
        if frame is None or frame.size == 0:
            logger.warning("frame_id=%d — empty/null frame received", frame_id)
            return FrameDetectionOutput(frame_id=frame_id, detections=[])

        t0 = time.perf_counter()

        # ── Run YOLOv8 inference ─────────────────────────────────────────────
        raw_detections = self._run_inference(frame)

        # ── Apply temporal smoothing (optional) ──────────────────────────────
        if self._enable_smoothing:
            stable_detections = self._smoother.update(raw_detections)
        else:
            stable_detections = raw_detections

        # ── Build output ─────────────────────────────────────────────────────
        output = FrameDetectionOutput(
            frame_id=frame_id,
            detections=stable_detections,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if LOG_INTERMEDIATE_STATES:
            logger.info(
                "frame_id=%d | raw=%d stable=%d | %.1f ms",
                frame_id, len(raw_detections), output.count, elapsed_ms,
            )

        return output

    def reset_stream(self) -> None:
        """
        Reset temporal smoother state.
        Call when switching to a new video stream or after a long gap.
        """
        self._smoother.reset()
        logger.info("PersonDetector stream state reset.")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_model(self, model_path: str, device: str):
        """
        Load YOLOv8 model via ultralytics.
        Device + half-precision are applied at predict() call time
        (ultralytics ≥8.x preferred API) to avoid .model.half() internals.
        Falls back to CPU if CUDA is unavailable or OOM.
        """
        try:
            from ultralytics import YOLO  # type: ignore
            model = YOLO(model_path)
            logger.info(
                "YOLOv8 model loaded: %s (will run on %s, half=%s)",
                model_path, device, HALF_PRECISION,
            )
            return model
        except ImportError:
            logger.error(
                "ultralytics not installed. Run: pip install ultralytics"
            )
            raise
        except Exception as exc:
            logger.error("Failed to load model '%s': %s", model_path, exc)
            raise

    def _run_inference(self, frame: np.ndarray) -> "list[DetectionResult]":
        """
        Execute YOLOv8 inference and return filtered DetectionResult list.

        Steps
        -----
        1. Run model with built-in NMS (conf + iou thresholds passed directly).
        2. Filter results: keep ONLY 'person' class (class_id == 0).
        3. Convert [x1, y1, x2, y2] → [x, y, width, height].
        4. Cap at MAX_DETECTIONS.
        """
        try:
            results = self._model.predict(
                source=frame,
                conf=self._conf,
                iou=self._nms_iou,
                classes=[PERSON_CLASS_ID],   # hard-filter: person only
                max_det=MAX_DETECTIONS,
                device=self._device,
                half=HALF_PRECISION,
                verbose=False,
            )
        except RuntimeError as exc:
            # CUDA OOM or device error — retry on CPU
            if "cuda" in str(exc).lower() or "out of memory" in str(exc).lower():
                logger.warning("CUDA error (%s) — retrying on CPU.", exc)
                self._device = "cpu"
                results = self._model.predict(
                    source=frame,
                    conf=self._conf,
                    iou=self._nms_iou,
                    classes=[PERSON_CLASS_ID],
                    max_det=MAX_DETECTIONS,
                    device="cpu",
                    half=False,
                    verbose=False,
                )
            else:
                raise

        detections: list[DetectionResult] = []

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes
            xyxy = boxes.xyxy.cpu().numpy()     # [N, 4] — x1,y1,x2,y2
            confs = boxes.conf.cpu().numpy()    # [N]
            cls_ids = boxes.cls.cpu().numpy()   # [N]

            for i in range(len(xyxy)):
                # Double-check class (should already be filtered by `classes=`)
                if int(cls_ids[i]) != PERSON_CLASS_ID:
                    continue

                x1, y1, x2, y2 = xyxy[i]
                w = x2 - x1
                h = y2 - y1
                conf = float(confs[i])

                detections.append(DetectionResult(
                    bbox=[float(x1), float(y1), float(w), float(h)],
                    confidence=conf,
                ))

        logger.debug(
            "_run_inference: %d persons detected (pre-smoothing)",
            len(detections),
        )
        return detections
