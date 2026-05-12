from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
from flask import Flask, Response, jsonify, send_from_directory

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from project_paths import ARTIFACTS_DIR, ROOT_DIR

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api_security import ApiAuthConfig, require_api_auth
from face_node_factory import build_face_node
from output_delivery_module.supabase_client import (
    DatabaseAlertReader,
    SupabaseAlertReader,
    SupabaseConfig,
)
from person_detection_module.config import MODEL_PATH
from run_surveillance_pipeline import _draw_overlay
from surveillance_backend_pipeline import SurveillanceBackendPipeline


class LivePipelineService:
    def __init__(
        self,
        source,
        backend: str,
        model_path: str,
        conf: float,
        face_mode: str,
        edge_face_api: Optional[str],
    ) -> None:
        self.source = source
        self.backend = backend
        self.model_path = model_path
        self.conf = conf
        self.face_mode = face_mode
        self.edge_face_api = edge_face_api
        self.lock = threading.Lock()
        self.latest_state: dict = {"status": "initializing"}
        self.latest_frame_bytes: Optional[bytes] = None
        self.last_update_at: Optional[float] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.output_path = ARTIFACTS_DIR / "latest_pipeline_output.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self) -> None:
        from multi_object_tracking_module.tracker import MultiObjectTracker
        from person_detection_module.detector import PersonDetector

        detector = PersonDetector(model_path=self.model_path, conf_threshold=self.conf)
        tracker = MultiObjectTracker(backend=self.backend)
        face_node = build_face_node(self.face_mode, self.edge_face_api)
        pipeline = SurveillanceBackendPipeline(face_node=face_node)

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            with self.lock:
                self.latest_state = {
                    "status": "error",
                    "message": f"Cannot open source: {self.source}",
                    "updated_at": time.time(),
                }
            return

        frame_id = 0
        try:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    with self.lock:
                        self.latest_state = {
                            "status": "error",
                            "message": "Failed to read frame from source",
                            "updated_at": time.time(),
                        }
                    break

                detection_output = detector.detect(frame, frame_id)
                tracking_output = tracker.update(detection_output, frame=frame)
                result = pipeline.process(detection_output, tracking_output, frame)
                payload = result.to_dict()
                payload["status"] = "running"
                payload["updated_at"] = time.time()

                overlay = _draw_overlay(frame, result)
                success, encoded = cv2.imencode(".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if success:
                    frame_bytes = encoded.tobytes()
                else:
                    frame_bytes = None

                with self.output_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)

                with self.lock:
                    self.latest_state = payload
                    self.latest_frame_bytes = frame_bytes
                    self.last_update_at = payload["updated_at"]

                frame_id += 1
        finally:
            cap.release()
            try:
                pipeline.height_node.close()
            except Exception:
                pass

    def get_state(self) -> dict:
        with self.lock:
            return dict(self.latest_state)

    def get_frame(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_frame_bytes

    def get_readiness(self) -> dict:
        with self.lock:
            state = dict(self.latest_state)
            frame_available = self.latest_frame_bytes is not None
            updated_at = self.last_update_at or state.get("updated_at")

        now = time.time()
        frame_age = (now - float(updated_at)) if updated_at else None
        ready = (
            state.get("status") == "running"
            and frame_available
            and frame_age is not None
            and frame_age <= 5.0
        )
        return {
            "status": "ready" if ready else "not_ready",
            "ready": ready,
            "frame_available": frame_available,
            "frame_age_seconds": round(frame_age, 3) if frame_age is not None else None,
            "pipeline_status": state.get("status", "unknown"),
            "details": state if not ready else {},
        }


def create_app(
    service: LivePipelineService,
    auth_required: Optional[bool] = None,
    allow_localhost_bypass: Optional[bool] = None,
) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(ROOT_DIR / "surveillance-dashboard-module"),
        static_url_path="",
    )

    dashboard_dir = ROOT_DIR / "surveillance-dashboard-module"
    enable_remote_alerts = os.getenv("ENABLE_REMOTE_ALERTS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    supabase_config = SupabaseConfig.from_env()
    db_alert_reader = (
        DatabaseAlertReader(supabase_config)
        if enable_remote_alerts and supabase_config and supabase_config.database_url
        else None
    )
    rest_alert_reader = (
        SupabaseAlertReader(supabase_config)
        if enable_remote_alerts and supabase_config
        else None
    )
    auth_config = ApiAuthConfig.from_env(
        required_override=auth_required,
        allow_localhost_bypass_override=allow_localhost_bypass,
    )
    if auth_config.required and not auth_config.secret:
        raise RuntimeError("API_AUTH_REQUIRED is enabled but API_JWT_SECRET is missing")

    def _require_auth(view):
        return require_api_auth(auth_config)(view)

    @app.route("/live")
    def api_live():
        return jsonify({"status": "alive"})

    @app.route("/ready")
    def api_ready():
        readiness = service.get_readiness()
        status_code = 200 if readiness["ready"] else 503
        return jsonify(readiness), status_code

    @app.route("/")
    def dashboard_index():
        return send_from_directory(dashboard_dir, "index.html")

    @app.route("/styles.css")
    def dashboard_styles():
        return send_from_directory(dashboard_dir, "styles.css")

    @app.route("/app.js")
    def dashboard_app():
        return send_from_directory(dashboard_dir, "app.js")

    @app.route("/api/state")
    @_require_auth
    def api_state():
        return jsonify(service.get_state())

    @app.route("/api/alerts")
    @_require_auth
    def api_alerts():
        if not enable_remote_alerts:
            return jsonify({"source": "disabled", "alerts": []})
        limit = 25
        if db_alert_reader is not None:
            try:
                return jsonify({"source": "database", "alerts": db_alert_reader.fetch_recent(limit=limit)})
            except Exception:
                pass
        if rest_alert_reader is not None:
            try:
                return jsonify({"source": "rest", "alerts": rest_alert_reader.fetch_recent(limit=limit)})
            except Exception as exc:
                return jsonify({"source": "rest", "alerts": [], "error": str(exc)}), 502
        return jsonify({"source": "none", "alerts": []})

    @app.route("/api/frame.jpg")
    @_require_auth
    def api_frame():
        frame = service.get_frame()
        if frame is None:
            return Response(status=503)
        return Response(frame, mimetype="image/jpeg")

    @app.route("/api/stream.mjpg")
    @_require_auth
    def api_stream():
        def generate():
            while True:
                frame = service.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
                time.sleep(0.08)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app


def parse_args():
    parser = argparse.ArgumentParser(description="Connected surveillance dashboard service")
    parser.add_argument("--source", default="0", help="Webcam index or video path")
    parser.add_argument("--backend", default="deepsort", choices=["deepsort", "bytetrack"])
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--model", default=MODEL_PATH)
    parser.add_argument(
        "--face-mode",
        default="recognition",
        choices=["recognition", "edge", "none"],
        help="Use full face recognition, edge-only face detection, or disable face signal",
    )
    parser.add_argument(
        "--edge-face-api",
        default="",
        help="ESP32 face endpoint base URL, e.g. http://192.168.1.100",
    )
    parser.add_argument(
        "--auth-required",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Require JWT auth on data endpoints when enabled",
    )
    parser.add_argument(
        "--allow-localhost-bypass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Allow localhost requests to bypass JWT checks",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main():
    args = parse_args()
    source = int(args.source) if str(args.source).isdigit() else args.source
    service = LivePipelineService(
        source=source,
        backend=args.backend,
        model_path=args.model,
        conf=args.conf,
        face_mode=args.face_mode,
        edge_face_api=args.edge_face_api or None,
    )
    service.start()
    app = create_app(
        service,
        auth_required=args.auth_required,
        allow_localhost_bypass=args.allow_localhost_bypass,
    )
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
