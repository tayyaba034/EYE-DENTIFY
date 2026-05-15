from explainability_module import ExplainabilityEngine


def test_explainability_engine_generates_human_readable_reason():
    explanation = ExplainabilityEngine().build(
        final_score=0.84,
        face_score=0.87,
        clothing_color="blue",
        clothing_score=0.74,
        temporal_validated=True,
        consecutive_frames=6,
    )

    assert "Final score 0.84" in explanation
    assert "blue" in explanation
    assert "6 consecutive frames" in explanation
