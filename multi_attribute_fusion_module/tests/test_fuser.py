from multi_attribute_fusion_module import FusionEngine, FusionInput


def test_fusion_prefers_face_when_available():
    engine = FusionEngine()

    result = engine.fuse(
        FusionInput(track_id=1, face_score=0.8, clothing_score=0.6, temporal_score=0.9)
    )

    assert round(result.final_score, 4) == 0.74
    assert round(result.contribution["face"], 4) == 0.56
    assert round(result.contribution["clothing"], 4) == 0.18
    assert result.contribution["temporal"] == 0.0


def test_fusion_rebalances_when_face_missing():
    engine = FusionEngine()

    result = engine.fuse(
        FusionInput(track_id=2, face_score=None, clothing_score=0.6, temporal_score=0.8)
    )

    assert round(result.final_score, 4) == 0.7
    assert round(result.contribution["clothing"], 4) == 0.3
    assert round(result.contribution["temporal"], 4) == 0.4
