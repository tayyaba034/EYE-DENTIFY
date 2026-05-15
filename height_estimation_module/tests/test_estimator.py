import numpy as np

from height_estimation_module import HeightEstimator


class _Track:
    def __init__(self, track_id, bbox):
        self.track_id = track_id
        self.bbox = bbox


class _TrackingOutput:
    def __init__(self, confirmed_tracks):
        self.confirmed_tracks = confirmed_tracks


def test_height_estimator_returns_coarse_height_signal():
    estimator = HeightEstimator()
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    tracking_output = _TrackingOutput([_Track(4, [10, 20, 30, 100])])

    results = estimator.process(tracking_output, frame)

    assert len(results) == 1
    assert results[0].track_id == 4
    assert 0.0 <= results[0].estimated_height_m <= 2.0
    assert 0.0 <= results[0].confidence <= 0.85
    assert isinstance(results[0].pose_detected, bool)
    assert isinstance(results[0].landmarks, list)
