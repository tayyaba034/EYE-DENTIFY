from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional


@dataclass
class AlertDecisionResult:
    track_id: int
    alert: bool
    priority: str
    reason: str
    explanation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "alert": self.alert,
            "priority": self.priority,
            "reason": self.reason,
            "explanation": self.explanation,
            "confidence": round(self.confidence, 4),
        }


class AlertDecisionEngine:
    def __init__(
        self,
        threshold: float = 0.75,
        cooldown_seconds: int = 30,
    ) -> None:
        self.threshold = threshold
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self._last_alert_at: Dict[int, datetime] = {}

    def evaluate(
        self,
        track_id: int,
        validated: bool,
        final_score: float,
        contributions: dict,
        now: Optional[datetime] = None,
    ) -> AlertDecisionResult:
        timestamp = now or datetime.now(UTC)
        score = max(0.0, min(1.0, float(final_score)))

        if not validated:
            return AlertDecisionResult(
                track_id=track_id,
                alert=False,
                priority="low",
                reason="temporal_validation_failed",
                explanation=self._build_explanation(False, score, contributions),
                confidence=score,
            )

        last_alert = self._last_alert_at.get(track_id)
        if last_alert is not None and timestamp - last_alert < self.cooldown:
            return AlertDecisionResult(
                track_id=track_id,
                alert=False,
                priority="low",
                reason="cooldown_active",
                explanation="Alert suppressed because cooldown is still active.",
                confidence=score,
            )

        if score < self.threshold:
            return AlertDecisionResult(
                track_id=track_id,
                alert=False,
                priority="low",
                reason="score_below_threshold",
                explanation=self._build_explanation(False, score, contributions),
                confidence=score,
            )

        self._last_alert_at[track_id] = timestamp
        return AlertDecisionResult(
            track_id=track_id,
            alert=True,
            priority=self._priority(score),
            reason="validated_score_above_threshold",
            explanation=self._build_explanation(True, score, contributions),
            confidence=score,
        )

    @staticmethod
    def _priority(score: float) -> str:
        if score >= 0.9:
            return "high"
        if score >= 0.82:
            return "medium"
        return "low"

    @staticmethod
    def _build_explanation(alert: bool, score: float, contributions: dict) -> str:
        decision_text = "Alert triggered" if alert else "Alert suppressed"
        return (
            f"{decision_text}: final score {score:.2f}, "
            f"face {contributions.get('face', 0.0):.2f}, "
            f"clothing {contributions.get('clothing', 0.0):.2f}, "
            f"temporal {contributions.get('temporal', 0.0):.2f}."
        )
