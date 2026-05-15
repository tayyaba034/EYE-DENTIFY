from __future__ import annotations


class ExplainabilityEngine:
    def build(
        self,
        *,
        final_score: float,
        face_score: float | None,
        clothing_color: str | None,
        clothing_score: float | None,
        temporal_validated: bool,
        consecutive_frames: int,
    ) -> str:
        face_text = (
            f"facial similarity contributed {face_score:.2f}"
            if face_score is not None
            else "face signal was unavailable"
        )
        clothing_text = (
            f"clothing signal {clothing_color} contributed {clothing_score:.2f}"
            if clothing_score is not None and clothing_color
            else "clothing signal was weak or unavailable"
        )
        temporal_text = (
            f"temporal validation passed across {consecutive_frames} consecutive frames"
            if temporal_validated
            else f"temporal validation not yet satisfied after {consecutive_frames} frames"
        )
        return (
            f"Final score {final_score:.2f}: {face_text}; "
            f"{clothing_text}; {temporal_text}."
        )
