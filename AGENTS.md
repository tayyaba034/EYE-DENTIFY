# AGENTS.md

## Purpose
This repository is a modular surveillance intelligence pipeline. Its main runtime flow is:

1. Person detection
2. Multi-object tracking
3. Feature extraction
4. Multi-attribute fusion
5. Temporal validation
6. Alert decision
7. Output delivery
8. Live dashboard/API serving

The codebase is organized as a backend-first pipeline with a lightweight frontend dashboard in `surveillance-dashboard-module/`.

## Main Entry Points

### `run_surveillance_pipeline.py`
Primary local runner for end-to-end processing from webcam/video/image source.

- Builds `PersonDetector`
- Builds `MultiObjectTracker`
- Builds `FaceExtractorNode`
- Injects face node into `SurveillanceBackendPipeline`
- Reads frames with OpenCV
- Runs detection -> tracking -> backend pipeline
- Writes JSON output to `runtime/artifacts/latest_pipeline_output.json`
- Optionally renders OpenCV overlay window unless `--headless`
- Supports `--face-mode recognition|edge|none` and `--edge-face-api` for face signal selection
- Current local webcam runs are expected to use `--source 0` unless the camera is exposed on a different index

CLI flags:

- `--source`: webcam index or path
- `--backend`: `deepsort` or `bytetrack`
- `--conf`: detection confidence threshold
- `--model`: detector weights path
- `--json-out`: output artifact path
- `--headless`: disables GUI
- `--max-frames`: bounded run for testing

### `surveillance_live_service.py`
Flask service that runs the same pipeline in a background thread and exposes:

- `/api/state`: latest pipeline JSON payload
- `/api/frame.jpg`: latest JPEG frame
- `/api/stream.mjpg`: MJPEG stream
- `/api/alerts`: recent remote alerts if enabled
- `/`: dashboard HTML/CSS/JS

Important behavior:

- `LivePipelineService` owns the video loop and shared state
- JSON state is persisted to `runtime/artifacts/latest_pipeline_output.json`
- Dashboard assets are served from `surveillance-dashboard-module/`
- Remote alert fetching is gated by `ENABLE_REMOTE_ALERTS`
- The service is currently the preferred way to run the laptop webcam pipeline with the browser dashboard attached
- In this workspace, `face_node_factory.build_face_node('recognition', None)` falls back to a pure OpenCV Haar cascade face detector when the InsightFace import chain is unavailable

### Current local run behavior

- The browser dashboard at `/` reads from `/api/state`, `/api/alerts`, and `/api/stream.mjpg`
- The local webcam path is working with `python surveillance_live_service.py --source 0 --face-mode recognition`
- Stop the running pipeline by interrupting the terminal that launched `surveillance_live_service.py` or by closing that terminal

### `surveillance_backend_pipeline.py`
Core orchestrator for non-web backend stages. This is the most important integration file.

It wires together:

- `ClothingFeatureExtractor`
- `HeightEstimator`
- `FusionEngine`
- `TemporalValidator`
- `AlertDecisionEngine`
- `ExplainabilityEngine`
- `OutputDeliveryEngine`

Its `process(detection_output, tracking_output, frame)` method is the canonical stage-joining contract.

## Directory Map

- `person_detection_module/`: Stage 1 detection
- `multi_object_tracking_module/`: Stage 2 tracking
- `facial_recognition_module/`: Stage 3A face verification
- `clothing_feature_extraction_module/`: Stage 3B clothing features
- `height_estimation_module/`: Stage 3C optional height estimation
- `multi_attribute_fusion_module/`: Stage 4 fusion
- `temporal_validation_module/`: Stage 5 temporal stability
- `alert_decision_module/`: Stage 6 alerting rules
- `explainability_module/`: human-readable explanation strings
- `output_delivery_module/`: snapshot saving and Supabase publishing
- `surveillance-dashboard-module/`: HTML/CSS/JS dashboard
- `runtime/`: generated artifacts and logs
- `supabase/`: migration/config artifacts
- `tests/`: pipeline/service/json tests at repo root

Non-runtime documentation folders:

- `ESP32/`, `MULTI_CAM/`, and multiple root `.md` files are design/reference material, not part of the active Python runtime path.

## Pipeline Contracts

### Stage 1: Person Detection
Files:

- `person_detection_module/detector.py`
- `person_detection_module/temporal_smoother.py`
- `person_detection_module/schemas.py`
- `person_detection_module/config.py`

Behavior:

- Uses Ultralytics YOLO
- Restricts detections to COCO `person` class
- Converts boxes to `[x, y, w, h]`
- Applies detection-level temporal smoothing before emitting
- Returns `FrameDetectionOutput`

Important defaults from config:

- confidence threshold: `0.50`
- NMS IoU: `0.45`
- smoothing window: `3`
- minimum consecutive frames before emission: `2`

Key design note:

- Detection smoothing is not tracking. It is only meant to suppress flicker before Stage 2.

### Stage 2: Multi-Object Tracking
Files:

- `multi_object_tracking_module/tracker.py`
- `multi_object_tracking_module/bytetrack_adapter.py`
- `multi_object_tracking_module/deepsort_adapter.py`
- `multi_object_tracking_module/schemas.py`
- `multi_object_tracking_module/config.py`

Behavior:

- Accepts `FrameDetectionOutput`
- Emits `FrameTrackingOutput`
- Supports `bytetrack` and `deepsort`
- Downstream modules usually operate only on `confirmed_tracks`

Backend details:

- ByteTrack implementation here is a lightweight in-repo approximation, not a full external tracker implementation
- DeepSORT uses `deep-sort-realtime` and requires the raw frame for appearance embeddings
- Default tracker config file says `bytetrack`, but CLI/service default args currently prefer `deepsort`

Track semantics:

- `track_id` means continuity token only
- It is not an identity label

### Stage 3A: Facial Recognition
File:

- `facial_recognition_module/src/face_node.py`

Behavior:

- Uses InsightFace `FaceAnalysis` when available
- Runs only on `confirmed_tracks`
- Crops tracked person region, then detects face inside that crop
- Applies quality gates:
  - detection score
  - blur variance
  - yaw/pitch thresholds
- Compares embedding to reference embeddings in `facial_recognition_module/data/03-features/reference_embeddings.npz`
- Returns `face_score` only, not a final identity decision

Caching:

- The node caches successful track results in `embedding_cache`
- Once cached for a `track_id`, later frames reuse the prior face result

Operational note:

- This can make a track’s face result sticky across frames until the track disappears or the node is reset
- On this machine, the default local webcam path uses an OpenCV Haar cascade fallback if the InsightFace import stack fails during startup

### Stage 3B: Clothing Feature Extraction
File:

- `clothing_feature_extraction_module/clothing_node.py`

Behavior:

- Operates on `confirmed_tracks`
- Extracts torso ROI
- Optionally uses Haar face detection to anchor torso crop
- Classifies coarse color buckets:
  - red
  - green
  - blue
  - yellow
  - orange
  - white
  - black
  - grey
- Smooths color over per-track history

Optional env-based behavior:

- `CLOTHING_TARGET_COLOR` can be used for simple target matching metadata

### Stage 3C: Height Estimation
File:

- `height_estimation_module/estimator.py`

Behavior:

- Optional support signal, not primary identity signal
- Attempts pose-based height estimation with:
  - local YOLO pose model `yolov8n-pose.pt`
  - optional MediaPipe landmarker if task file exists
  - optional ArUco calibration if markers are visible
- Falls back to coarse bbox-height heuristic if pose data is unavailable

Output:

- estimated height in meters
- confidence
- pose detected flag
- landmarks when available

Important note:

- The estimator exposes `close()` for MediaPipe cleanup
- `surveillance_live_service.py` calls this in the background-thread cleanup path

### Stage 4: Fusion
File:

- `multi_attribute_fusion_module/fuser.py`

Behavior:

- Combines face, clothing, and optionally temporal/height scores into one `final_score`
- In current implementation:
  - if face exists, weights normalize across face and clothing
  - if face is absent, weights normalize across clothing and temporal
  - height contribution is explicitly multiplied by `0.0`

Important implementation detail:

- `surveillance_backend_pipeline.py` never passes a temporal score into `FusionInput`
- That means temporal does not currently contribute to fusion in practice
- Height is computed but intentionally contributes nothing to final score

So the effective current fusion is mostly:

- face + clothing when face is available
- clothing only when face is unavailable

### Stage 5: Temporal Validation
File:

- `temporal_validation_module/validator.py`

Behavior:

- Tracks recent fused scores by `track_id`
- Requires:
  - score >= threshold for consecutive frames
  - stability score >= `0.6`
  - low frame-to-frame oscillation

Defaults:

- minimum consecutive frames: `5`
- score threshold: `0.65`
- history size: `10`

This is the real anti-spike gate before alerting.

### Stage 6: Alert Decision
File:

- `alert_decision_module/decision.py`

Behavior:

- Requires temporal validation first
- Applies final alert threshold
- Enforces per-track cooldown
- Returns:
  - alert boolean
  - priority
  - reason
  - explanation
  - confidence

Defaults:

- alert threshold: `0.75`
- cooldown: `30` seconds

Priority mapping:

- `>= 0.90`: high
- `>= 0.82`: medium
- otherwise low

### Stage 7: Explainability and Output Delivery
Files:

- `explainability_module/engine.py`
- `output_delivery_module/delivery.py`
- `output_delivery_module/supabase_client.py`

Behavior:

- Builds a short human-readable explanation string
- Saves track crop snapshots into `runtime/artifacts/alerts/`
- Publishes alert payload to Supabase if configured
- DB publisher is preferred when `database_url` is available
- REST publisher is fallback

Remote integrations:

- `SupabaseConfig.from_env()` loads values from root `.env`
- Supported env names include:
  - `SUPABASE_URL`
  - `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `DATABASE_URL`, `DIRECT_URL`, or `SUPABASE_DB_URL`
  - `SUPABASE_ALERTS_TABLE`

## Runtime Artifacts

Generated during normal operation:

- `runtime/artifacts/latest_pipeline_output.json`
- `runtime/artifacts/alerts/*.jpg`
- `runtime/logs/*`

Path setup is centralized in `project_paths.py`, which ensures these directories exist at import time.

## Dashboard
Files:

- `surveillance-dashboard-module/index.html`
- `surveillance-dashboard-module/styles.css`
- `surveillance-dashboard-module/app.js`

Behavior:

- Polls `/api/state` every 2.5s
- Polls `/api/alerts`
- Streams `/api/stream.mjpg`
- Renders:
  - stage summary
  - alert list
  - fusion results
  - track table
  - delivery records

Data expectations:

- Dashboard assumes the backend JSON contains `detections`, `tracks`, `face_features`, `clothing_features`, `height_features`, `fusion`, `temporal`, `alerts`, and `deliveries`

## Tests

Root tests:

- `tests/test_surveillance_backend_pipeline.py`
- `tests/test_live_service.py`
- `tests/test_json_serialization.py`

Module tests also exist under several module directories.

Current root test coverage confirms:

- backend pipeline orchestrates non-web stages
- temporal validation eventually flips to true
- JSON serialization handles numpy scalars
- Flask `/api/state` endpoint responds

`pytest.ini` excludes caches and sets local pytest cache directory under `.cache/pytest`.

## Environment and Dependencies

### Environment loading
`env_config.py` loads the root `.env` lazily via `python-dotenv`.

### Important caution
The repository currently contains a populated `.env` with sensitive-looking credentials. Do not copy secrets into prompts, commits, tickets, or generated docs. Refer to variable names only.

### Python dependencies inferred from code
Core runtime dependencies include:

- `opencv-python`
- `numpy`
- `ultralytics`
- `flask`
- `python-dotenv`
- `psycopg`
- `insightface`
- `onnxruntime`
- `deep-sort-realtime` for DeepSORT mode
- optional `mediapipe` for richer height estimation
- `torch`

### Bundled assets/models
Large model files are stored inside the repo, including examples like:

- `yolov8n-pose.pt`
- `person_detection_module/yolov8n.pt`
- `multi_object_tracking_module/yolov8s.pt`
- `facial_recognition_module/src/yolov8n.pt`
- `height_estimation_module/yolov8n-pose.pt`

There is also a nested virtual environment under `height_estimation_module/venv310_new/`; treat it as vendor noise, not source of truth.

## Non-Obvious Implementation Notes

### 1. Effective fusion logic is narrower than the docs imply
Although the project describes face + clothing + height + temporal fusion, the actual score currently used for alerts is effectively:

- face + clothing, or
- clothing only

because:

- height contribution is forced to zero in `FusionEngine`
- temporal score is not passed into `FusionInput`

### 2. Temporal validation is downstream of fusion, not part of it
Temporal validation gates alerts after fusion. It is not currently feeding back into the fused score.

### 3. Face results are cached per `track_id`
This improves speed but can preserve stale face matches for a continuing track.

### 4. Tracker backend defaults differ by layer

- tracker config module default: `bytetrack`
- CLI/service argument defaults: `deepsort`

When debugging behavior differences, check which entry point constructed the tracker.

### 5. Database schema handling looks inconsistent
`supabase/migrations/20260329_create_alerts_table.sql` creates a primary key column named `id`, but `DatabaseAlertPublisher.publish()` and `DatabaseAlertReader.fetch_recent()` query `alert_id`, plus additional columns like `priority`, `status`, and `alert_level` that are not created by the shown migration.

Interpretation:

- either the live Supabase table evolved outside this migration
- or local schema assumptions are stale/inconsistent

Future DB changes should reconcile migration files and Python query expectations.

### 6. `create_app()` treats dashboard serving as local static hosting
The frontend is not a separate SPA build system; it is plain static assets served directly by Flask.

### 7. Root docs are partially aspirational
Files like `pipeline.md` describe the intended design well, but code should be treated as source of truth when behavior differs.

### 8. Current overlay is intentionally simpler
The live overlay currently draws:

- person detection boxes
- confirmed track boxes
- face boxes
- pose landmarks and pose connections for height estimation

It no longer draws the clothing region bounding box, but clothing color text and clothing feature values are still emitted in the JSON payload.

### 9. Local face startup is fallback-driven
The local face-node factory now prefers the InsightFace-backed path but falls back to an OpenCV Haar cascade detector when that stack cannot be imported cleanly in the active environment.

That means the laptop webcam pipeline can run without needing ESP32 face input, even if the InsightFace dependency chain is incomplete.

## Recommended Workflow For Future Agents

When making changes, start from these files first:

1. `surveillance_backend_pipeline.py`
2. `run_surveillance_pipeline.py`
3. `surveillance_live_service.py`
4. The specific module being changed
5. Related tests under root `tests/` and module `tests/`

When debugging pipeline behavior:

1. Confirm detector output shape
2. Confirm tracker state and whether tracks are `confirmed`
3. Check whether feature extractors are returning empty/default results
4. Inspect fusion output
5. Inspect temporal validator counters
6. Check alert threshold/cooldown
7. Verify delivery/Supabase behavior separately from inference

## Safe Assumptions

- Bounding boxes are represented as `[x, y, w, h]` in most pipeline contracts
- Downstream stages usually expect confirmed tracks only
- `runtime/` contents are generated artifacts and can change frequently
- Docs under `ESP32/` and `MULTI_CAM/` are context/reference, not core runtime dependencies

## Known Risks / Technical Debt

- Sensitive `.env` is present in repo
- In-repo nested virtual environment adds noise to file searches
- DB schema references appear out of sync with migration file
- Fusion implementation does not yet match full multi-signal design intent
- Face cache can become stale for long-lived tracks
- Test coverage does not fully validate real external integrations or full model-backed inference

## Quick Summary
If you need the shortest accurate mental model for this repo:

- `run_surveillance_pipeline.py` and `surveillance_live_service.py` are the two main entry points
- `surveillance_backend_pipeline.py` is the integration hub
- alerts depend on confirmed tracks, feature extraction, fusion score, temporal stability, and threshold/cooldown logic
- dashboard is plain static JS consuming Flask APIs
- Supabase integration exists but schema assumptions may need cleanup
- the current alert score is driven mainly by face and clothing, despite broader architectural docs
- the current local webcam workflow is `surveillance_live_service.py --source 0 --face-mode recognition`, with an OpenCV fallback if InsightFace startup is unavailable




Set-Location "d:/FYP MODELS/plschalja/PIPELINE"; & "d:/FYP MODELS/plschalja/.venv/Scripts/python.exe" surveillance_live_service.py --source 0 --host 127.0.0.1 --port 8000