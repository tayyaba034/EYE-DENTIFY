from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import cv2

from output_delivery_module.supabase_client import (
    DatabaseAlertPublisher,
    SupabaseAlertPublisher,
    SupabaseConfig,
)
from project_paths import ALERTS_DIR


@dataclass
class DeliveryRecord:
    track_id: int
    timestamp: str
    confidence: float
    explanation: str
    snapshot: Optional[str]
    remote_status: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "timestamp": self.timestamp,
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation,
            "snapshot": self.snapshot,
            "remote_status": self.remote_status,
        }


class OutputDeliveryEngine:
    def __init__(self, snapshot_dir: Optional[str] = None) -> None:
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else ALERTS_DIR
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        config = SupabaseConfig.from_env()
        self.db_publisher = DatabaseAlertPublisher(config) if config and config.database_url else None
        self.publisher = SupabaseAlertPublisher(config) if config else None

    def create_record(
        self,
        *,
        track_id: int,
        confidence: float,
        explanation: str,
        frame=None,
        bbox=None,
    ) -> DeliveryRecord:
        timestamp = datetime.now(UTC).isoformat()
        snapshot_path = None
        if frame is not None and bbox is not None:
            snapshot_path = self._save_snapshot(track_id, frame, bbox)
        remote_status = None
        payload = {
            "track_id": track_id,
            "timestamp": timestamp,
            "confidence": confidence,
            "explanation": explanation,
            "snapshot": snapshot_path,
        }
        if self.db_publisher is not None:
            try:
                remote_status = self.db_publisher.publish(payload)
            except Exception as exc:
                remote_status = {"ok": False, "mode": "database", "error": str(exc)}
        if (not remote_status or not remote_status.get("ok")) and self.publisher is not None:
            remote_status = self.publisher.publish(payload)
        return DeliveryRecord(
            track_id=track_id,
            timestamp=timestamp,
            confidence=confidence,
            explanation=explanation,
            snapshot=snapshot_path,
            remote_status=remote_status,
        )

    def _save_snapshot(self, track_id: int, frame, bbox) -> Optional[str]:
        x, y, w, h = [int(v) for v in bbox]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        output_path = self.snapshot_dir / f"track_{track_id}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.jpg"
        cv2.imwrite(str(output_path), crop)
        return str(output_path)
