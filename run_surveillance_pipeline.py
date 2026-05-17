from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

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
logger = logging.getLogger("run_surveillance_pipeline")


def parse_args():
    parser = argparse.ArgumentParser(description="End-to-end surveillance backend runner")
    parser.add_argument("--source", default="0", help="Webcam index or video/image path")
    parser.add_argument("--backend", default="bytetrack", choices=["deepsort", "bytetrack"])
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
    parser.add_argument("--json-out", default=str(ARTIFACTS_DIR / "latest_pipeline_output.json"))
    parser.add_argument("--headless", action="store_true", help="Run without GUI display")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    return parser.parse_args()


def _draw_labeled_box(vis, box, color, label, thickness=2):
    x, y, w, h = [int(v) for v in box]
    cv2.rectangle(vis, (x, y), (x + w, y + h), color, thickness)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.42
    text_thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, text_thickness)
    pad_x = 5
    pad_y = 3
    label_x1 = x
    label_y2 = max(text_h + baseline + pad_y * 2, y)
    label_y1 = label_y2 - (text_h + baseline + pad_y * 2)
    label_x2 = x + text_w + pad_x * 2

    cv2.rectangle(vis, (label_x1, label_y1), (label_x2, label_y2), color, -1)
    cv2.putText(
        vis,
        label,
        (label_x1 + pad_x, label_y2 - baseline - pad_y),
        font,
        font_scale,
        (15, 15, 15),
        text_thickness,
        cv2.LINE_AA,
    )


def _draw_overlay(frame, result):
    vis = frame.copy()
    face_by_track = {item["track_id"]: item for item in result.face_features}
    clothing_by_track = {item["track_id"]: item for item in result.clothing_features}
    height_by_track = {item["track_id"]: item for item in result.height_features}
    temporal_by_track = {item["track_id"]: item for item in result.temporal}
    fusion_by_track = {item["track_id"]: item for item in result.fusion}
    alerts_by_track = {item["track_id"]: item for item in result.alerts}

    pose_connections = [
        (11, 12), # shoulders
        (11, 23), # L-shoulder to L-hip
        (12, 24), # R-shoulder to R-hip
        (23, 24), # hips
        (23, 25), # L-hip to L-knee
        (24, 26), # R-hip to R-knee
        (25, 27), # L-knee to L-ankle
        (26, 28), # R-knee to R-ankle
        (11, 13), # L-shoulder to L-elbow
        (13, 15), # L-elbow to L-wrist
        (12, 14), # R-shoulder to R-elbow
        (14, 16), # R-elbow to R-wrist
        # Left Hand
        (15, 17), (15, 21), (17, 19), (19, 21),
        # Right Hand
        (16, 18), (16, 22), (18, 20), (20, 22),
        # Left Foot
        (27, 29), (27, 31), (29, 31),
        # Right Foot
        (28, 30), (28, 32), (30, 32),
    ]

    for det in result.detections["detections"]:
        _draw_labeled_box(vis, det["bbox"], (0, 210, 255), "person detect", thickness=1)

    for track in result.tracks["tracks"]:
        x, y, w, h = [int(v) for v in track["bbox"]]
        color = (0, 255, 0) if track["state"] == "confirmed" else (0, 180, 255)
        _draw_labeled_box(
            vis,
            track["bbox"],
            color,
            f"track {track['track_id']}",
            thickness=2,
        )
        face = face_by_track.get(track["track_id"], {})
        clothing = clothing_by_track.get(track["track_id"], {}).get("clothing", {})
        height = height_by_track.get(track["track_id"], {}).get("height", {})
        fusion = fusion_by_track.get(track["track_id"], {})
        temporal = temporal_by_track.get(track["track_id"], {})
        alert = alerts_by_track.get(track["track_id"], {})

        face_detected = face.get("face_detected", False)
        face_score = face.get("face_score", 0.0)
        face_text = (
            f"face match {face_score:.2f}" if face_detected and face_score >= 0.40
            else f"face not matched {face_score:.2f}" if face_detected
            else "face unavailable"
        )
        clothing_text = f"{clothing.get('color', 'unknown')} {clothing.get('confidence', 0.0):.2f}"
        fusion_text = f"fusion {fusion.get('final_score', 0.0):.2f}"
        temporal_text = (
            f"validated {temporal.get('consecutive_frames', 0)}f"
            if temporal.get("validated")
            else f"pending {temporal.get('consecutive_frames', 0)}f"
        )

        details = [
            f"state {track['state']}",
            face_text,
            f"cloth {clothing_text}",
            fusion_text,
            temporal_text,
        ]
        if height:
            details.append(f"height {height.get('estimated_height_m', 0.0):.2f}m")
        if alert.get("alert"):
            details.append(f"alert {alert.get('priority', 'low')}")

        for idx, line in enumerate(details):
            cv2.putText(
                vis,
                line,
                (x, y + h + 18 + idx * 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (225, 235, 245),
                1,
                cv2.LINE_AA,
            )

        if face_detected and "face_bbox" in face:
            fx1, fy1, fx2, fy2 = [int(v) for v in face["face_bbox"]]
            face_color = (0, 255, 0) if face_score >= 0.40 else (0, 0, 255)
            _draw_labeled_box(
                vis,
                [fx1, fy1, fx2 - fx1, fy2 - fy1],
                face_color,
                "face region",
                thickness=2,
            )

        if height.get("pose_detected") and height_by_track.get(track["track_id"], {}).get("landmarks"):
            landmark_map = {
                int(item["id"]): (int(item["x"]), int(item["y"]), float(item["visibility"]))
                for item in height_by_track[track["track_id"]]["landmarks"]
            }
            for start_id, end_id in pose_connections:
                if start_id in landmark_map and end_id in landmark_map:
                    sx, sy, sv = landmark_map[start_id]
                    ex, ey, ev = landmark_map[end_id]
                    if sv >= 0.4 and ev >= 0.4:
                        cv2.line(vis, (sx, sy), (ex, ey), (255, 200, 0), 2)
            for _, (px, py, visibility) in landmark_map.items():
                point_color = (255, 220, 0) if visibility >= 0.5 else (120, 120, 120)
                cv2.circle(vis, (px, py), 4, point_color, -1)

    return vis


def main():
    args = parse_args()
    source = int(args.source) if args.source.isdigit() else args.source

    detector = PersonDetector(model_path=args.model, conf_threshold=args.conf)
    tracker = MultiObjectTracker(backend=args.backend)
    face_node = build_face_node(args.face_mode, args.edge_face_api or None)
    pipeline = SurveillanceBackendPipeline(face_node=face_node)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source}")

    output_path = Path(args.json_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detection_output = detector.detect(frame, frame_id)
        tracking_output = tracker.update(detection_output, frame=frame)
        result = pipeline.process(detection_output, tracking_output, frame)

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result.to_dict(), handle, indent=2)

        if frame_id % 15 == 0:
            logger.info(
                "frame=%d det=%d tracks=%d alerts=%d",
                frame_id,
                len(result.detections["detections"]),
                len(result.tracks["tracks"]),
                len([a for a in result.alerts if a["alert"]]),
            )

        if not args.headless:
            vis = _draw_overlay(frame, result)
            cv2.imshow("Surveillance Backend Pipeline", vis)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

        frame_id += 1
        if args.max_frames and frame_id >= args.max_frames:
            break

    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
