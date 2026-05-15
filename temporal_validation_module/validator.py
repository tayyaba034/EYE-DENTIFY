from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass
class TemporalValidationResult:
    track_id: int
    validated: bool
    stability_score: float
    consecutive_frames: int

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "validated": self.validated,
            "stability_score": round(self.stability_score, 4),
            "consecutive_frames": self.consecutive_frames,
        }


class TemporalValidator:
    def __init__(
        self,
        min_consecutive_frames: int = 5,
        score_threshold: float = 0.65,
        history_size: int = 10,
    ) -> None:
        self._min_consecutive_frames = min_consecutive_frames
        self._score_threshold = score_threshold
        self._history: Dict[int, Deque[float]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self._consecutive_hits: Dict[int, int] = defaultdict(int)

    def update(self, track_id: int, final_score: float) -> TemporalValidationResult:
        score = max(0.0, min(1.0, float(final_score)))
        self._history[track_id].append(score)

        if score >= self._score_threshold:
            self._consecutive_hits[track_id] += 1
        else:
            self._consecutive_hits[track_id] = 0

        stability_score = self._compute_stability(self._history[track_id])
        stable_sequence = self._is_stable_sequence(self._history[track_id])
        validated = (
            self._consecutive_hits[track_id] >= self._min_consecutive_frames
            and stability_score >= 0.6
            and stable_sequence
        )
        return TemporalValidationResult(
            track_id=track_id,
            validated=validated,
            stability_score=stability_score,
            consecutive_frames=self._consecutive_hits[track_id],
        )

    def reset(self) -> None:
        self._history.clear()
        self._consecutive_hits.clear()

    def _compute_stability(self, history: Deque[float]) -> float:
        if not history:
            return 0.0
        mean_score = sum(history) / len(history)
        if len(history) == 1:
            return round(mean_score, 4)
        deltas = [abs(history[i] - history[i - 1]) for i in range(1, len(history))]
        oscillation_penalty = min(1.0, sum(deltas) / len(deltas))
        return round(max(0.0, mean_score * (1.0 - 0.5 * oscillation_penalty)), 4)

    @staticmethod
    def _is_stable_sequence(history: Deque[float]) -> bool:
        if len(history) < 2:
            return False
        deltas = [abs(history[i] - history[i - 1]) for i in range(1, len(history))]
        return max(deltas) <= 0.15
