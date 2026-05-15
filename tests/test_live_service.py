import numpy as np

from surveillance_live_service import create_app


class _DummyService:
    def get_state(self):
        return {"status": "running", "frame_id": 3, "updated_at": 1_700_000_000.0}

    def get_frame(self):
        return np.zeros((10, 10, 3), dtype=np.uint8).tobytes()

    def get_readiness(self):
        return {
            "status": "ready",
            "ready": True,
            "frame_available": True,
            "frame_age_seconds": 0.5,
            "pipeline_status": "running",
            "details": {},
        }


def test_live_service_state_endpoint():
    app = create_app(_DummyService())
    client = app.test_client()

    response = client.get("/api/state")

    assert response.status_code == 200
    assert response.json["status"] == "running"


def test_live_service_readiness_endpoint():
    app = create_app(_DummyService())
    client = app.test_client()

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json["ready"] is True
