"""
deepsort_adapter.py — DeepSORT Adapter
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

Wraps the deep_sort_realtime library exposing the same update() interface
as ByteTrackAdapter so the tracker backend is swappable via config.

DeepSORT Strategy
-----------------
* Kalman filter for motion prediction (position + velocity).
* Appearance re-ID features (CNN embeddings) for robust re-association.
* Mahalanobis distance for motion matching + cosine distance for appearance.
* Confirmed tracks require N_INIT consecutive detections.
"""

from __future__ import annotations
import logging
from typing import List, Tuple

from multi_object_tracking_module.config import (
    DEVICE,
    DS_MAX_AGE,
    DS_N_INIT,
    DS_MAX_IOU_DISTANCE,
    DS_MAX_COSINE_DISTANCE,
    DS_NN_BUDGET,
)
from multi_object_tracking_module.schemas import TrackedPerson

logger = logging.getLogger(__name__)

_STATE_MAP = {
    1: "tentative",   # DeepSORT internal: Tentative
    2: "confirmed",   # DeepSORT internal: Confirmed
    3: "lost",        # DeepSORT internal: Deleted (we prune these)
}


class DeepSORTAdapter:
    """
    DeepSORT-based multi-object tracker.

    Requires: pip install deep-sort-realtime

    Usage
    -----
    tracker = DeepSORTAdapter()
    tracked = tracker.update(detections, frame, frame_id)
    """

    def __init__(self) -> None:
        self._tracker = self._init_tracker()
        self._frames_seen: dict[int, int] = {}   # track_id → frames_seen count

    def _init_tracker(self):
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort  # type: ignore
            tracker = DeepSort(
                max_age=DS_MAX_AGE,
                n_init=DS_N_INIT,
                max_iou_distance=DS_MAX_IOU_DISTANCE,
                max_cosine_distance=DS_MAX_COSINE_DISTANCE,
                nn_budget=DS_NN_BUDGET,
                override_track_class=None,
                embedder="mobilenet",       # lightweight built-in embedder
                half=DEVICE != "cpu",
                bgr=True,
                embedder_gpu=DEVICE != "cpu",
            )
            logger.info("DeepSORT tracker initialised.")
            return tracker
        except ImportError:
            logger.error(
                "deep-sort-realtime not installed. "
                "Run: pip install deep-sort-realtime"
            )
            raise

    def update(
        self,
        detections: List[Tuple[List[float], float]],  # [(bbox [x,y,w,h], conf)]
        frame,          # numpy BGR frame (needed for re-ID embedding)
        frame_id: int,
    ) -> List[TrackedPerson]:
        """
        Parameters
        ----------
        detections : [(bbox, confidence)] from Stage 1.
        frame      : Raw BGR numpy frame for appearance embedding.
        frame_id   : Current frame index.

        Returns
        -------
        List[TrackedPerson] (use .confirmed_tracks on FrameTrackingOutput).
        """
        # Convert to ([x,y,w,h], conf, class) format DeepSort expects
        ds_input = [(b, c, "person") for b, c in detections]

        raw_tracks = self._tracker.update_tracks(ds_input, frame=frame)

        result: List[TrackedPerson] = []
        for track in raw_tracks:
            if not track.is_confirmed() and track.time_since_update > 1:
                continue

            tid = int(track.track_id)
            ltrb = track.to_ltrb()  # [x1, y1, x2, y2]
            x, y = ltrb[0], ltrb[1]
            w, h = ltrb[2] - ltrb[0], ltrb[3] - ltrb[1]

            # Track consecutive frames seen
            self._frames_seen[tid] = self._frames_seen.get(tid, 0) + 1

            state = "confirmed" if track.is_confirmed() else "tentative"

            result.append(TrackedPerson(
                track_id=tid,
                bbox=[x, y, w, h],
                confidence=track.det_conf if track.det_conf is not None else 0.0,
                state=state,
                frames_seen=self._frames_seen[tid],
            ))

        logger.debug(
            "DeepSORT frame=%d | dets=%d tracks=%d",
            frame_id, len(detections), len(result),
        )
        return result

    def reset(self) -> None:
        self._tracker = self._init_tracker()
        self._frames_seen.clear()
