# EYE-DENTIFY

EYE-DENTIFY is a modular, real-time surveillance intelligence pipeline that combines person detection, multi-object tracking, face and clothing signals, height estimation, fusion, temporal validation, explainability, alerting, and live dashboard delivery.

## Project Structure

- `person_detection_module/` — YOLOv8-based person detection (Stage 1)
- `multi_object_tracking_module/` — ByteTrack/DeepSORT tracking (Stage 2)
- `facial_recognition_module/` — face recognition/edge face signal
- `clothing_feature_extraction_module/` — clothing color/confidence extraction
- `height_estimation_module/` — pose-based height estimation
- `multi_attribute_fusion_module/` — score fusion engine
- `temporal_validation_module/` — temporal confidence validation
- `explainability_module/` — human-readable explanation generation
- `alert_decision_module/` — alert priority and decision logic
- `output_delivery_module/` — alert payload packaging and output delivery
- `surveillance-dashboard-module/` — frontend dashboard assets
- `surveillance_live_service.py` — Flask service for live dashboard + API endpoints
- `run_surveillance_pipeline.py` — backend pipeline runner

## Quick Start

1. Create a virtual environment and install dependencies.
2. Run the live service:

```bash
python surveillance_live_service.py --source 0 --backend deepsort --face-mode recognition
```

3. Open the dashboard at:

```text
http://localhost:8000/
```

For RunPod deployment instructions, see `RUNPOD_DEPLOYMENT.md`.

## Testing

```bash
python -m pytest -q
```

## Contributors

- **Tayyaba034** — Project owner and maintainer
- **Amna** — Contributor

## Branches

- `main` — primary project branch
- `copilot/amna-add-readme-file` — Amna's branch
