"""
esp32_ingestion_module/esp32_capture.py
-----------------------------------------
``ESP32FrameCapture`` is a drop-in replacement for ``cv2.VideoCapture``
that serves frames from ``FrameStore`` instead of a physical camera.

Why a wrapper class instead of patching cv2?
--------------------------------------------
The existing pipeline passes ``cap`` through only two call sites:
  1. ``cap.isOpened()``  — checked once at start
  2. ``cap.read()``      — called in the frame loop

Matching this interface makes the diff to ``surveillance_live_service.py``
minimal: just swap the construction line.

Blocking vs polling
--------------------
``read()`` can operate in two modes:

  * ``blocking=True``  (default): waits up to ``timeout_s`` for a new
    frame from the ESP32. Best for throughput — no busy-polling.
  * ``blocking=False``: returns the most recent frame immediately, or
    (False, None) if no frame is available. Use this if the pipeline
    should keep producing output even when the camera is slow.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import numpy as np

from .frame_store import FrameStore, StoredFrame

logger = logging.getLogger(__name__)


class ESP32FrameCapture:
    """
    Mimics the ``cv2.VideoCapture`` interface.

    Usage (replacing the existing VideoCapture line):
    ::

        # REMOVE:  cap = cv2.VideoCapture(self.source)
        # ADD:
        cap = ESP32FrameCapture(frame_store, blocking=True, timeout_s=8.0)

    Then the existing ``cap.isOpened()`` / ``cap.read()`` calls work unchanged.
    """

    def __init__(
        self,
        frame_store: FrameStore,
        blocking: bool = True,
        timeout_s: float = 8.0,
        max_age_s: float = 10.0,
    ) -> None:
        """
        Parameters
        ----------
        frame_store:
            Shared ``FrameStore`` populated by the Flask upload route.
        blocking:
            If True, ``read()`` blocks until a frame arrives (up to
            ``timeout_s``).  If False, ``read()`` returns immediately.
        timeout_s:
            Maximum seconds to wait per ``read()`` call in blocking mode.
        max_age_s:
            Frames older than this are treated as unavailable.
        """
        self._store      = frame_store
        self._blocking   = blocking
        self._timeout_s  = timeout_s
        self._max_age_s  = max_age_s
        self._opened     = True              # always open; store may be empty
        self._last_id    = -1               # track duplicates (optional)
        self._read_count = 0
        self._miss_count = 0

    # ── cv2.VideoCapture compatibility ────────────────────────────────────

    def isOpened(self) -> bool:            # noqa: N802 (match cv2 naming)
        """Always True — there is no physical device to open."""
        return self._opened

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Return (True, frame_bgr) when a fresh frame is available.
        Return (False, None) on timeout or stale data.
        """
        stored: Optional[StoredFrame]

        if self._blocking:
            stored = self._store.wait_for_frame(timeout_s=self._timeout_s)
        else:
            stored = self._store.get_frame(max_age_s=self._max_age_s)

        if stored is None:
            self._miss_count += 1
            if self._miss_count % 10 == 1:
                logger.warning(
                    "[ESP32Capture] No frame available (miss #%d). "
                    "Is the ESP32-CAM sending frames to /api/esp32/frame ?",
                    self._miss_count,
                )
            return False, None

        self._read_count += 1
        self._miss_count = 0    # reset consecutive-miss counter on success

        if stored.frame_id == self._last_id:
            # Same frame as last read — still valid, just not new
            logger.debug("[ESP32Capture] Serving repeated frame #%d", stored.frame_id)
        self._last_id = stored.frame_id

        return True, stored.frame.copy()   # copy: pipeline may mutate the array

    def release(self) -> None:
        """No-op (no device to release)."""
        self._opened = False
        logger.info(
            "[ESP32Capture] Released. read=%d miss=%d",
            self._read_count, self._miss_count,
        )

    def get(self, prop_id: int) -> float:           # noqa: ARG002
        """Stub — returns 0.0 for all VideoCapture properties."""
        return 0.0

    def set(self, prop_id: int, value: float) -> bool:  # noqa: ARG002
        """Stub — silently accepts all property sets."""
        return True

    # ── Extra helpers ─────────────────────────────────────────────────────

    @property
    def frame_store(self) -> FrameStore:
        return self._store
