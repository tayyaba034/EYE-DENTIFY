"""
multicam_live_service.py
Multi-camera surveillance live service.

Runs multiple camera sources in a background thread (round-robin or priority-failover)
and exposes the same Flask API surface as surveillance_live_service.py so the dashboard
can consume it without changes.

Usage:
    python multicam_live_service.py --sources 0,1
    python multicam_live_service.py --sources "rtsp://cam1/stream,rtsp://cam2/stream"
    python multicam_live_service.py --sources 0,1 --priority-failover --match-signal face
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("multicam_live_service")


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers (mirrored from run_multicam_surveillance.py)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_csv(values: str) -> List[str]:
    return [item.strip() for item in values.split(",") if item.strip()]


def _parse_source(source: str):
    return int(source) if source.isdigit() else source


def _has_confirmed_track(camera_payload: Dict) -> bool:
    tracks = camera_payload.get("pipeline", {}).get("tracks", {}).get("tracks", [])
    return any(t.get("state") == "confirmed" for t in tracks)


def _has_face_detected(camera_payload: Dict) -> bool:
    features = camera_payload.get("pipeline", {}).get("face_features", [])
    return any(bool(item.get("face_detected")) for item in features)


def _has_alert(camera_payload: Dict) -> bool:
    alerts = camera_payload.get("pipeline", {}).get("alerts", [])
    return any(bool(item.get("alert")) for item in alerts)


def _camera_has_match(camera_payload: Dict, match_signal: str) -> bool:
    if camera_payload.get("status") != "running":
        return False
    if match_signal == "face":
        return _has_face_detected(camera_payload)
    if match_signal == "alert":
        return _has_alert(camera_payload)
    return _has_confirmed_track(camera_payload)


# ─────────────────────────────────────────────────────────────────────────────
#  Per-camera runtime container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CameraRuntime:
    camera_id: str
    source_raw: str
    cap: cv2.VideoCapture
    detector: object
    tracker: object
    pipeline: SurveillanceBackendPipeline
    frame_id: int = 0
    last_frame: Optional[object] = None  # latest raw numpy frame


# ─────────────────────────────────────────────────────────────────────────────
#  Multi-camera live service
# ─────────────────────────────────────────────────────────────────────────────

class MultiCamLiveService:
    """
    Runs N camera sources in a single background thread.

    Modes:
    - parallel        : every camera is processed every cycle
    - priority_failover: cameras are checked in order; processing stops at the
                         first camera that satisfies match_signal
    """

    def __init__(
        self,
        sources: List[str],
        backend: str,
        model_path: str,
        conf: float,
        face_mode: str,
        edge_face_apis: List[str],
        priority_failover: bool,
        match_signal: str,
    ) -> None:
        self.sources = sources
        self.backend = backend
        self.model_path = model_path
        self.conf = conf
        self.face_mode = face_mode
        self.edge_face_apis = edge_face_apis
        self.priority_failover = priority_failover
        self.match_signal = match_signal

        self.lock = threading.Lock()
        self.latest_state: dict = {"status": "initializing"}
        # Per-camera latest JPEG bytes keyed by camera_id
        self.latest_frames: Dict[str, Optional[bytes]] = {}
        # The camera_id whose frame is currently "active" for the MJPEG stream
        self.active_camera_id: Optional[str] = None
        self.last_update_at: Optional[float] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.output_path = ARTIFACTS_DIR / "latest_multicam_pipeline_output.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _build_runtimes(self) -> List[CameraRuntime]:
        from multi_object_tracking_module.tracker import MultiObjectTracker
        from person_detection_module.detector import PersonDetector

        runtimes: List[CameraRuntime] = []
        for index, source_raw in enumerate(self.sources):
            source = _parse_source(source_raw)
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                logger.error("Cannot open camera source: %s — skipping", source_raw)
                continue

            detector = PersonDetector(model_path=self.model_path, conf_threshold=self.conf)
            tracker = MultiObjectTracker(backend=self.backend)
            edge_api = self.edge_face_apis[index] if self.face_mode == "edge" and index < len(self.edge_face_apis) else None
            face_node = build_face_node(self.face_mode, edge_api)
            pipeline = SurveillanceBackendPipeline(face_node=face_node)
            runtimes.append(
                CameraRuntime(
                    camera_id=f"cam_{index + 1}",
                    source_raw=source_raw,
                    cap=cap,
                    detector=detector,
                    tracker=tracker,
                    pipeline=pipeline,
                )
            )
        return runtimes

    def _run_loop(self) -> None:
        runtimes = self._build_runtimes()
        if not runtimes:
            with self.lock:
                self.latest_state = {"status": "error", "message": "No cameras could be opened"}
            return

        logger.info("MultiCamLiveService started with %d cameras", len(runtimes))
        cycle = 0

        try:
            while not self.stop_event.is_set():
                payload: dict = {
                    "status": "running",
                    "cycle": cycle,
                    "timestamp": int(time.time() * 1000),
                    "updated_at": time.time(),
                    "cameras": [],
                    "active_camera_id": None,
                    "mode": "priority_failover" if self.priority_failover else "parallel",
                    "match_signal": self.match_signal,
                }

                camera_results: List[Dict] = []
                active_camera_found = False
                new_frames: Dict[str, Optional[bytes]] = {}
                active_cam_id: Optional[str] = None

                for runtime in runtimes:
                    # In priority-failover mode, skip lower-priority cameras once a match is found
                    if self.priority_failover and active_camera_found:
                        camera_results.append({
                            "camera_id": runtime.camera_id,
                            "source": runtime.source_raw,
                            "status": "standby",
                            "reason": "higher-priority camera already matched",
                        })
                        continue

                    ok, frame = runtime.cap.read()
                    if not ok:
                        camera_results.append({
                            "camera_id": runtime.camera_id,
                            "source": runtime.source_raw,
                            "status": "error",
                            "message": "failed to read frame",
                        })
                        continue

                    runtime.last_frame = frame
                    detection_output = runtime.detector.detect(frame, runtime.frame_id)
                    tracking_output = runtime.tracker.update(detection_output, frame=frame)
                    result = runtime.pipeline.process(detection_output, tracking_output, frame)
                    runtime.frame_id += 1

                    # Encode JPEG for this camera
                    from run_surveillance_pipeline import _draw_overlay
                    overlay = _draw_overlay(frame, result)
                    success, encoded = cv2.imencode(
                        ".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                    )
                    new_frames[runtime.camera_id] = encoded.tobytes() if success else None

                    camera_payload = {
                        "camera_id": runtime.camera_id,
                        "source": runtime.source_raw,
                        "status": "running",
                        "pipeline": result.to_dict(),
                    }
                    camera_results.append(camera_payload)

                    if self.priority_failover and _camera_has_match(camera_payload, self.match_signal):
                        payload["active_camera_id"] = runtime.camera_id
                        active_cam_id = runtime.camera_id
                        active_camera_found = True

                # In parallel mode, active camera is the first running one
                if not self.priority_failover:
                    for cr in camera_results:
                        if cr.get("status") == "running":
                            active_cam_id = cr["camera_id"]
                            payload["active_camera_id"] = active_cam_id
                            break

                if self.priority_failover and payload["active_camera_id"] is None:
                    payload["active_camera_id"] = "none"

                payload["cameras"] = camera_results

                # Persist JSON
                with self.output_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)

                with self.lock:
                    self.latest_state = payload
                    self.latest_frames.update(new_frames)
                    self.active_camera_id = active_cam_id
                    self.last_update_at = payload["updated_at"]

                cycle += 1

        finally:
            for runtime in runtimes:
                runtime.cap.release()
                try:
                    runtime.pipeline.height_node.close()
                except Exception:
                    pass

    def get_state(self) -> dict:
        with self.lock:
            return dict(self.latest_state)

    def get_active_frame(self) -> Optional[bytes]:
        """Return JPEG bytes for the currently active camera."""
        with self.lock:
            cam_id = self.active_camera_id
            if cam_id is None:
                return None
            return self.latest_frames.get(cam_id)

    def get_camera_frame(self, camera_id: str) -> Optional[bytes]:
        """Return JPEG bytes for a specific camera."""
        with self.lock:
            return self.latest_frames.get(camera_id)

    def get_readiness(self) -> dict:
        with self.lock:
            state = dict(self.latest_state)
            frame_available = any(v is not None for v in self.latest_frames.values())
            updated_at = self.last_update_at or state.get("updated_at")

        now = time.time()
        frame_age = (now - float(updated_at)) if updated_at else None
        ready = (
            state.get("status") == "running"
            and frame_available
            and frame_age is not None
            and frame_age <= 10.0
        )
        return {
            "status": "ready" if ready else "not_ready",
            "ready": ready,
            "frame_available": frame_available,
            "frame_age_seconds": round(frame_age, 3) if frame_age is not None else None,
            "pipeline_status": state.get("status", "unknown"),
            "camera_count": len(self.latest_frames),
            "active_camera_id": self.active_camera_id,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Flask app
# ─────────────────────────────────────────────────────────────────────────────

def create_multicam_app(
    service: MultiCamLiveService,
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
        "1", "true", "yes", "on",
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
        return jsonify(readiness), (200 if readiness["ready"] else 503)

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
        """
        Returns multi-cam payload:
        {
          "status": "running",
          "mode": "parallel" | "priority_failover",
          "active_camera_id": "cam_1",
          "cameras": [
            { "camera_id": "cam_1", "status": "running", "pipeline": { ... } },
            { "camera_id": "cam_2", "status": "running", "pipeline": { ... } },
          ]
        }
        """
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
        """Returns JPEG for the currently active camera."""
        frame = service.get_active_frame()
        if frame is None:
            return Response(status=503)
        return Response(frame, mimetype="image/jpeg")

    @app.route("/api/frame/<camera_id>.jpg")
    @_require_auth
    def api_camera_frame(camera_id: str):
        """Returns JPEG for a specific camera by ID (e.g. cam_1, cam_2)."""
        frame = service.get_camera_frame(camera_id)
        if frame is None:
            return Response(status=503)
        return Response(frame, mimetype="image/jpeg")

    @app.route("/api/stream.mjpg")
    @_require_auth
    def api_stream():
        """MJPEG stream for the active camera."""
        def generate():
            while True:
                frame = service.get_active_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
                time.sleep(0.08)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/stream/<camera_id>.mjpg")
    @_require_auth
    def api_camera_stream(camera_id: str):
        """MJPEG stream for a specific camera."""
        def generate():
            while True:
                frame = service.get_camera_frame(camera_id)
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


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-camera surveillance live service")
    parser.add_argument(
        "--sources",
        required=True,
        help="Comma-separated camera sources: indices, paths, or RTSP URLs. E.g. '0,1' or 'rtsp://cam1/stream,rtsp://cam2/stream'",
    )
    parser.add_argument("--backend", default="deepsort", choices=["deepsort", "bytetrack"])
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--model", default=MODEL_PATH)
    parser.add_argument(
        "--face-mode",
        default="none",
        choices=["recognition", "edge", "none"],
        help="Face signal mode. Use 'none' for CPU-only demo, 'recognition' for full pipeline.",
    )
    parser.add_argument(
        "--edge-face-apis",
        default="",
        help="Comma-separated ESP32 API base URLs matching --sources order (only for --face-mode=edge)",
    )
    parser.add_argument(
        "--priority-failover",
        action="store_true",
        help="Check cameras in order; stop at first camera that satisfies --match-signal",
    )
    parser.add_argument(
        "--match-signal",
        default="track",
        choices=["track", "face", "alert"],
        help="Signal used to declare a camera match in priority-failover mode",
    )
    parser.add_argument(
        "--auth-required",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--allow-localhost-bypass",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main():
    args = parse_args()
    sources = _parse_csv(args.sources)
    edge_face_apis = _parse_csv(args.edge_face_apis)

    service = MultiCamLiveService(
        sources=sources,
        backend=args.backend,
        model_path=args.model,
        conf=args.conf,
        face_mode=args.face_mode,
        edge_face_apis=edge_face_apis,
        priority_failover=args.priority_failover,
        match_signal=args.match_signal,
    )
    service.start()

    app = create_multicam_app(
        service,
        auth_required=args.auth_required,
        allow_localhost_bypass=args.allow_localhost_bypass,
    )
    logger.info("Starting multi-cam service on %s:%d with %d sources", args.host, args.port, len(sources))
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
