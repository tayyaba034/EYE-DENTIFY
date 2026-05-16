"""
esp32_ingestion_module/frame_store.py
--------------------------------------
Thread-safe ring buffer that stores the latest JPEG frame received
from the ESP32-CAM HTTP POST upload. The pipeline's capture thread
reads from this store instead of cv2.VideoCapture(0).

Design decisions
----------------
- Frames arrive as raw JPEG bytes; we decode to BGR numpy arrays here
  once, so the pipeline never needs to know the image arrived over HTTP.
- We keep only the **latest** frame (no queue), so a slow pipeline
  never accumulates a backlog of stale frames.
- Frame age is tracked so the pipeline can detect stale input.
- A threading.Event signals new-frame availability for polled callers.
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── Frame envelope ──────────────────────────────────────────────────────────

@dataclass
class StoredFrame:
    """One decoded frame plus its metadata."""
    frame:      np.ndarray        # BGR uint8 numpy array
    jpeg_bytes: bytes             # original JPEG for overlay streaming
    received_at: float            # Unix timestamp (time.time())
    frame_id:   int               # monotonically increasing
    camera_id:  str = "esp32"     # future: multi-camera support
    metadata:   dict = field(default_factory=dict)  # forwarded from ESP32


# ─── Frame store ─────────────────────────────────────────────────────────────

class FrameStore:
    """
    Singleton-style store for the latest ESP32-CAM frame.

    Thread safety: all public methods acquire self._lock.
    """

    def __init__(
        self,
        max_age_s: float = 10.0,
        target_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        """
        Parameters
        ----------
        max_age_s:
            Frames older than this are considered stale; ``get_frame``
            returns None for stale frames.
        target_size:
            If given, (width, height) tuple — incoming frames are
            resized to this resolution after decoding. Useful to
            normalise 320×240 ESP32 frames to whatever the pipeline
            expects (e.g. 640×480 for better detection accuracy).
        """
        self._lock           = threading.Lock()
        self._new_frame_evt  = threading.Event()
        self._latest: Optional[StoredFrame] = None
        self._max_age_s      = max_age_s
        self._target_size    = target_size   # (w, h) or None
        self._total_received = 0
        self._total_rejected = 0

    # ── Write path ────────────────────────────────────────────────────────

    def put_jpeg(
        self,
        jpeg_bytes: bytes,
        camera_id: str = "esp32",
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Decode a JPEG byte buffer and store the result.

        Returns True on success, False if the JPEG is unreadable.
        Called from the Flask upload route (a different thread than
        the pipeline loop).
        """
        if not jpeg_bytes:
            logger.warning("[FrameStore] Received empty payload — ignored.")
            self._total_rejected += 1
            return False

        # Decode JPEG → BGR numpy array
        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("[FrameStore] cv2.imdecode failed — not a valid JPEG.")
            self._total_rejected += 1
            return False

        # Optional resize (e.g. upscale from 320×240 → 640×480)
        if self._target_size is not None:
            frame = cv2.resize(frame, self._target_size, interpolation=cv2.INTER_LINEAR)

        with self._lock:
            frame_id = (self._latest.frame_id + 1) if self._latest else 0
            self._latest = StoredFrame(
                frame        = frame,
                jpeg_bytes   = jpeg_bytes,
                received_at  = time.time(),
                frame_id     = frame_id,
                camera_id    = camera_id,
                metadata     = metadata or {},
            )
            self._total_received += 1

        self._new_frame_evt.set()   # wake any blocking caller

        logger.debug(
            "[FrameStore] Stored frame #%d from %s  shape=%s",
            frame_id, camera_id, frame.shape,
        )
        return True

    # ── Read path ─────────────────────────────────────────────────────────

    def get_frame(self, max_age_s: Optional[float] = None) -> Optional[StoredFrame]:
        """
        Return the latest StoredFrame, or None if no frame has arrived
        yet or the most recent frame is older than max_age_s
        (defaults to self._max_age_s).
        """
        cutoff = max_age_s if max_age_s is not None else self._max_age_s
        with self._lock:
            stored = self._latest

        if stored is None:
            return None

        age = time.time() - stored.received_at
        if age > cutoff:
            logger.debug("[FrameStore] Frame #%d is stale (age=%.1fs).", stored.frame_id, age)
            return None

        return stored

    def wait_for_frame(self, timeout_s: float = 5.0) -> Optional[StoredFrame]:
        """
        Block until a new frame arrives (or timeout_s elapses).
        Clears the event after waking so the next call will block again.
        """
        self._new_frame_evt.wait(timeout=timeout_s)
        self._new_frame_evt.clear()
        return self.get_frame()

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Diagnostic dict for /api/esp32/status."""
        with self._lock:
            stored = self._latest

        frame_age = None
        if stored is not None:
            frame_age = round(time.time() - stored.received_at, 3)

        return {
            "frames_received": self._total_received,
            "frames_rejected": self._total_rejected,
            "latest_frame_id": stored.frame_id if stored else None,
            "latest_frame_age_s": frame_age,
            "latest_camera_id": stored.camera_id if stored else None,
            "max_age_s": self._max_age_s,
            "target_size": list(self._target_size) if self._target_size else None,
        }
