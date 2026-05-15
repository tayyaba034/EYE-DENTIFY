from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FusionInput:
    track_id: int
    face_score: Optional[float] = None
    clothing_score: Optional[float] = None
    temporal_score: Optional[float] = None
    height_score: Optional[float] = None


@dataclass
class FusionResult:
    track_id: int
    final_score: float
    contribution: dict

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "final_score": round(self.final_score, 4),
            "contribution": {
                key: round(value, 4) for key, value in self.contribution.items()
            },
        }


class FusionEngine:
    def __init__(
        self,
        face_weight: float = 0.7,
        clothing_weight: float = 0.3,
        temporal_weight_without_face: float = 0.5,
    ) -> None:
        self.face_weight = face_weight
        self.clothing_weight = clothing_weight
        self.temporal_weight_without_face = temporal_weight_without_face

    def fuse(self, item: FusionInput) -> FusionResult:
        face = self._clamp(item.face_score)
        clothing = self._clamp(item.clothing_score)
        temporal = self._clamp(item.temporal_score)
        height = self._clamp(item.height_score)

        if face is not None:
            weights = self._normalize_weights(
                face=self.face_weight,
                clothing=self.clothing_weight if clothing is not None else 0.0,
                temporal=0.0,
            )
        else:
            weights = self._normalize_weights(
                face=0.0,
                clothing=0.5 if clothing is not None else 0.0,
                temporal=self.temporal_weight_without_face if temporal is not None else 0.0,
            )

        contributions = {
            "face": (face or 0.0) * weights["face"],
            "clothing": (clothing or 0.0) * weights["clothing"],
            "temporal": (temporal or 0.0) * weights["temporal"],
            "height": 0.0 if height is None else height * 0.0,
        }
        return FusionResult(
            track_id=item.track_id,
            final_score=sum(contributions.values()),
            contribution=contributions,
        )

    @staticmethod
    def _normalize_weights(face: float, clothing: float, temporal: float) -> dict:
        total = face + clothing + temporal
        if total <= 0:
            return {"face": 0.0, "clothing": 0.0, "temporal": 0.0}
        return {
            "face": face / total,
            "clothing": clothing / total,
            "temporal": temporal / total,
        }

    @staticmethod
    def _clamp(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))
