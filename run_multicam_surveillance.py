from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import cv2

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from project_paths import ARTIFACTS_DIR, ROOT_DIR

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from face_node_factory import build_face_node
from multi_object_tracking_module.tracker import MultiObjectTracker
from person_detection_module.config import MODEL_PATH
from person_detection_module.detector import PersonDetector
from surveillance_backend_pipeline import SurveillanceBackendPipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_multicam_surveillance")


@dataclass
class CameraRuntime:
    camera_id: str
    source_raw: str
    cap: cv2.VideoCapture
    detector: PersonDetector
    tracker: MultiObjectTracker
    pipeline: SurveillanceBackendPipeline
    frame_id: int = 0


def _has_confirmed_track(camera_payload: Dict) -> bool:
    tracks = camera_payload.get("pipeline", {}).get("tracks", {}).get("tracks", [])
    for track in tracks:
        if track.get("state") == "confirmed":
            return True
    return False


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


def _parse_csv(values: str) -> List[str]:
    return [item.strip() for item in values.split(",") if item.strip()]


def _parse_source(source: str):
    if source.isdigit():
        return int(source)
    return source


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-camera surveillance backend runner")
    parser.add_argument(
        "--sources",
        required=True,
        help="Comma-separated camera sources (indices, paths, or stream URLs)",
    )
    parser.add_argument("--backend", default="deepsort", choices=["deepsort", "bytetrack"])
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--model", default=MODEL_PATH)
    parser.add_argument(
        "--face-mode",
        default="edge",
        choices=["recognition", "edge", "none"],
        help="Face signal mode for all cameras",
    )
    parser.add_argument(
        "--edge-face-apis",
        default="",
        help="Comma-separated ESP32 API base URLs matching --sources order",
    )
    parser.add_argument(
        "--json-out",
        default=str(ARTIFACTS_DIR / "latest_multicam_pipeline_output.json"),
    )
    parser.add_argument(
        "--priority-failover",
        action="store_true",
        help="Check cameras in order and stop at first matched camera",
    )
    parser.add_argument(
        "--match-signal",
        default="track",
        choices=["track", "face", "alert"],
        help="Signal used to declare camera match in failover mode",
    )
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N cycles (0 = unlimited)")
    return parser.parse_args()


def _build_runtimes(args) -> List[CameraRuntime]:
    source_values = _parse_csv(args.sources)
    if not source_values:
        raise ValueError("--sources must contain at least one source")

    edge_face_apis = _parse_csv(args.edge_face_apis)
    if args.face_mode == "edge":
        if len(edge_face_apis) != len(source_values):
            raise ValueError("--edge-face-apis count must match --sources when --face-mode=edge")

    runtimes: List[CameraRuntime] = []
    for index, source_raw in enumerate(source_values):
        source = _parse_source(source_raw)
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {source_raw}")

        detector = PersonDetector(model_path=args.model, conf_threshold=args.conf)
        tracker = MultiObjectTracker(backend=args.backend)
        edge_api = edge_face_apis[index] if args.face_mode == "edge" else None
        face_node = build_face_node(args.face_mode, edge_api)
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


def main():
    args = parse_args()
    output_path = Path(args.json_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    runtimes = _build_runtimes(args)
    logger.info("multicam started with %d cameras", len(runtimes))

    cycle = 0
    try:
        while True:
            payload = {
                "status": "running",
                "cycle": cycle,
                "timestamp": int(time.time() * 1000),
                "cameras": [],
                "active_camera_id": None,
                "mode": "priority_failover" if args.priority_failover else "parallel",
                "match_signal": args.match_signal,
            }

            camera_results: List[Dict] = []
            active_camera_found = False

            for runtime in runtimes:
                if args.priority_failover and active_camera_found:
                    camera_results.append(
                        {
                            "camera_id": runtime.camera_id,
                            "source": runtime.source_raw,
                            "status": "standby",
                            "reason": "higher-priority camera already matched",
                        }
                    )
                    continue

                ok, frame = runtime.cap.read()
                if not ok:
                    camera_results.append(
                        {
                            "camera_id": runtime.camera_id,
                            "source": runtime.source_raw,
                            "status": "error",
                            "message": "failed to read frame",
                        }
                    )
                    continue

                detection_output = runtime.detector.detect(frame, runtime.frame_id)
                tracking_output = runtime.tracker.update(detection_output, frame=frame)
                result = runtime.pipeline.process(detection_output, tracking_output, frame)
                runtime.frame_id += 1

                camera_payload = {
                    "camera_id": runtime.camera_id,
                    "source": runtime.source_raw,
                    "status": "running",
                    "pipeline": result.to_dict(),
                }
                camera_results.append(camera_payload)

                if args.priority_failover and _camera_has_match(camera_payload, args.match_signal):
                    payload["active_camera_id"] = runtime.camera_id
                    active_camera_found = True

            payload["cameras"] = camera_results

            if args.priority_failover and payload["active_camera_id"] is None:
                payload["active_camera_id"] = "none"

            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)

            cycle += 1
            if args.max_frames and cycle >= args.max_frames:
                break
    finally:
        for runtime in runtimes:
            runtime.cap.release()
            try:
                runtime.pipeline.height_node.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
