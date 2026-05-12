from pathlib import Path
import sys


MODULE_PARENT = Path(__file__).resolve().parents[2]
if str(MODULE_PARENT) not in sys.path:
    sys.path.insert(0, str(MODULE_PARENT))


from person_detection_module.schemas import DetectionResult
from person_detection_module.temporal_smoother import TemporalSmoother


def test_temporal_smoother_requires_consecutive_frames_before_emitting():
    smoother = TemporalSmoother()
    detection = DetectionResult(bbox=[10.0, 20.0, 30.0, 40.0], confidence=0.8)

    first = smoother.update([detection])
    second = smoother.update([detection])

    assert first == []
    assert len(second) == 1
    assert second[0].bbox == detection.bbox


def test_temporal_smoother_keeps_new_candidate_alive_without_immediate_miss():
    smoother = TemporalSmoother()
    detection = DetectionResult(bbox=[1.0, 2.0, 3.0, 4.0], confidence=0.9)

    smoother.update([detection])

    assert len(smoother._candidates) == 1
    assert smoother._candidates[0].missed == 0
