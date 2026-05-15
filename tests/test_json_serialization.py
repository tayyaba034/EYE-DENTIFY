import json

import numpy as np

from surveillance_backend_pipeline import BackendPipelineResult


def test_backend_pipeline_result_to_dict_handles_numpy_scalars():
    result = BackendPipelineResult(
        frame_id=1,
        detections={"detections": [{"confidence": np.float32(0.9)}]},
        tracks={"tracks": []},
        face_features=[{"track_id": 1, "face_score": np.float32(0.75)}],
        clothing_features=[],
        height_features=[],
        fusion=[],
        temporal=[],
        alerts=[],
        deliveries=[],
    )

    payload = result.to_dict()

    assert abs(payload["detections"]["detections"][0]["confidence"] - 0.9) < 1e-6
    assert abs(payload["face_features"][0]["face_score"] - 0.75) < 1e-6
    json.dumps(payload)
