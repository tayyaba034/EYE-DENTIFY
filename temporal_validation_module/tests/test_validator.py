from temporal_validation_module import TemporalValidator


def test_validates_after_five_consistent_frames():
    validator = TemporalValidator(min_consecutive_frames=5, score_threshold=0.65)

    last = None
    for score in [0.7, 0.72, 0.75, 0.78, 0.8]:
        last = validator.update(track_id=1, final_score=score)

    assert last is not None
    assert last.validated is True
    assert last.consecutive_frames == 5
    assert last.stability_score >= 0.6


def test_rejects_oscillating_signal():
    validator = TemporalValidator(min_consecutive_frames=5, score_threshold=0.65)

    last = None
    for score in [0.7, 0.95, 0.66, 0.93, 0.67]:
        last = validator.update(track_id=2, final_score=score)

    assert last is not None
    assert last.validated is False
