from datetime import datetime

import numpy as np

from person_detection_module.schemas import DetectionResult, FrameDetectionOutput
from multi_object_tracking_module.schemas import FrameTrackingOutput, TrackedPerson
from surveillance_backend_pipeline import SurveillanceBackendPipeline


class _FaceNode:
    def process(self, tracking_output, frame):
        return [
            {"track_id": track.track_id, "face_score": 0.85, "face_detected": True}
            for track in tracking_output.confirmed_tracks
        ]


def test_backend_pipeline_runs_all_non_web_stages():
    pipeline = SurveillanceBackendPipeline(face_node=_FaceNode())
    frame = np.zeros((120, 80, 3), dtype=np.uint8)
    frame[20:70, 20:60] = (255, 0, 0)

    detection_output = FrameDetectionOutput(
        frame_id=4,
        detections=[DetectionResult(bbox=[10.0, 10.0, 60.0, 90.0], confidence=0.91)],
    )
    tracking_output = FrameTrackingOutput(
        frame_id=4,
        tracks=[
            TrackedPerson(
                track_id=12,
                bbox=[10.0, 10.0, 60.0, 90.0],
                confidence=0.91,
                state="confirmed",
                frames_seen=6,
            )
        ],
    )

    for _ in range(4):
        pipeline.process(detection_output, tracking_output, frame)
    result = pipeline.process(detection_output, tracking_output, frame)

    assert result.frame_id == 4
    assert result.face_features[0]["track_id"] == 12
    assert result.clothing_features[0]["clothing"]["color"] == "blue"
    assert result.height_features[0]["track_id"] == 12
    assert result.fusion[0]["final_score"] > 0.0
    assert result.temporal[0]["validated"] is True
    assert result.alerts[0]["alert"] is True
    assert len(result.deliveries) == 1
