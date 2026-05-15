# Surveillance Pipeline — Product Deployment Specification

Version: 1.0
Last updated: 2026-05-01
Authors: Pipeline Team

## Executive Summary

This document consolidates the architecture, operational design, and deployment instructions needed to ship the surveillance intelligence pipeline (the "Pipeline") as a production-ready product. It is intended for DevOps, SRE, product, and engineering teams responsible for deploying, operating, and maintaining the system.

High-level goals:
- Reliable person detection and multi-attribute alerting
- Reproducible deployment (local, containerized, cloud)
- Secure handling of secrets and PII-sensitive artifacts
- Observability, testing, and upgradeability

## Project Overview

The Pipeline is a modular, backend-first system implemented in Python. Main runtime flow:
1. Person detection (YOLOv8)
2. Multi-object tracking (ByteTrack / DeepSORT)
3. Feature extraction (face, clothing, height)
4. Multi-attribute fusion
5. Temporal validation
6. Alert decision
7. Explainability + Output delivery (Supabase optional)
8. Live dashboard/API serving (Flask)

Primary entrypoints:
- `run_surveillance_pipeline.py` — local end-to-end runner
- `surveillance_live_service.py` — Flask service with dashboard and API

Core components (code locations):
- Detection: `person_detection_module/`
- Tracking: `multi_object_tracking_module/`
- Face: `facial_recognition_module/`
- Clothing: `clothing_feature_extraction_module/`
- Height: `height_estimation_module/`
- Fusion: `multi_attribute_fusion_module/`
- Temporal: `temporal_validation_module/`
- Decision: `alert_decision_module/`
- Explainability: `explainability_module/`
- Delivery: `output_delivery_module/`
- Orchestrator: `surveillance_backend_pipeline.py`

## Constraints and Non-Functional Requirements

- Latency: target 100–300 ms per frame on GPU-backed hosts; CPU-only targets are allowed but with reduced FPS.
- Availability: Aim for 99.5% service availability for single-region deployments.
- Privacy: avoid persisting full frames containing faces unless required by business; store only short-lived alert crops and metadata with strict access control.
- Extensibility: modules must be replaceable with minimal orchestrator changes.

## Prerequisites

- OS: Linux (preferred for cloud), Windows supported for local testing.
- Python: 3.10+ (matches project venv usage)
- GPU support (optional but recommended): CUDA 11.x / cuDNN compatible drivers for PyTorch/Ultralytics.
- External services: Supabase (optional) for alerts DB; S3-compatible object store optional for snapshots.

Core Python dependencies (representative):
- opencv-python
- numpy
- ultralytics
- flask
- python-dotenv
- insightface
- onnxruntime
- deep-sort-realtime (for DeepSORT)
- torch
- psycopg (or `asyncpg` per DB client)

Use the repository `requirements.txt` files per module as authoritative. Consider producing a consolidated `requirements.txt` or `pyproject.toml` for deployment packaging.

## Environment & Configuration

The code loads environment variables via `env_config.py`. Key envs (do not commit secrets):

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side)
- `DATABASE_URL` / `SUPABASE_DB_URL`
- `SUPABASE_ALERTS_TABLE`
- `CLOTHING_TARGET_COLOR` (optional)
- `ENABLE_REMOTE_ALERTS` (boolean)
- `MODEL_PATHS` (override detector/tracker model files)

Always use a `.env` file kept outside VCS or inject envs via your orchestration layer (Docker secrets, Kubernetes Secrets, or cloud secret managers).

## Run & Local Testing

Run locally for quick verification (copy `.env.example` to `.env` and set keys):

```bash
python run_surveillance_pipeline.py --source 0
python surveillance_live_service.py --source 0 --port 3000
```

Module-level test commands:

```bash
pytest -v
pytest person_detection_module/tests/
```

The pipeline produces runtime artifacts under `runtime/` including `runtime/artifacts/latest_pipeline_output.json` and alert crops.

## Packaging & Containerization

Recommendation: produce a Docker image for the backend and a small static-serving image for the dashboard.

Dockerfile (high-level guidance):
- Base: `nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04` for GPU images, or `python:3.11-slim` for CPU-only.
- Install OS deps: `ffmpeg`, `libglib2.0-0`, `libsm6`, `libxrender1`, etc.
- Copy repo, install Python deps via `pip install -r requirements.txt`.
- Expose ports for API (e.g., 3000) and health check endpoint.
- Entrypoint: `gunicorn -w 4 -b 0.0.0.0:3000 surveillance_live_service:app` or a supervisor running `surveillance_live_service.py`.

Docker Compose example (minimal):
- `backend`: pipeline image
- `redis`: optional (for caching/session or rate-limiting)
- `db`: optional (local Supabase or Postgres test instance)
- volumes: model files can be mounted from host or pulled during build

Notes:
- Keep large model files out of Docker layers where possible — mount them as volumes at runtime or fetch during container start from an artifacts bucket.

## Cloud Deployment Options

1) AWS ECS / Fargate (recommended for simpler ops)
- Build and push Docker images to ECR.
- Run backend as service with task definitions; attach GPU-enabled EC2 instance type (if GPUs are needed) or use GPU-enabled ECS cluster.
- Use Application Load Balancer in front of the service.
- Use Secrets Manager or Parameter Store for environment variables.

2) AWS EKS (Kubernetes)
- Helm chart components: backend deployment, dashboard ingress, configmap for model paths, secrets for keys.
- Use nodegroups with GPU instances for inference pods.
- HorizontalPodAutoscaler (HPA) based on CPU or custom metrics.
- Use PersistentVolume for model cache or mount from S3 via CSI driver.

3) GCP / Azure
- Use corresponding container registries and managed Kubernetes or VM groups; follow the same patterns for secrets and storage.

Provisioning considerations:
- Attach IAM roles with minimal privilege for DB and S3 access.
- Ensure network ACLs allow camera source connectivity if using RTSP streams from on-prem cameras.

## Database & Alerts — Supabase Integration

The repo has Supabase support in `output_delivery_module/`. Best practices:
- Use the service role key only from trusted backend services.
- Store `SUPABASE_SERVICE_ROLE_KEY` in a secure secret manager; do not expose it to the client.
- Validate the current migration files versus expected schema (note: repository migration vs code schema inconsistencies were observed in AGENTS.md). Reconcile column names (`id` vs `alert_id`) before production writes.
- Consider introducing a migration CI check to ensure runtime schema matches code.

Alternative: If Supabase is not used, swap the `DatabaseAlertPublisher` with an S3 + Postgres or custom REST sink.

## CI / CD Pipeline (GitHub Actions example)

Suggested pipeline stages:
- lint: `black`, `ruff`, `isort`
- test: `pytest --maxfail=1 --disable-warnings -q`
- build: build Docker image (no model files) and push to registry
- infra: run `terraform plan` (if infra-as-code used)
- deploy: rollout to staging; run smoke tests

Example job snippet:

```yaml
jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: pytest -v
      - name: Build Docker image
        run: docker build -t ${{ secrets.REGISTRY }}/pipeline:${{ github.sha }} .
      - name: Push
        run: docker push ${{ secrets.REGISTRY }}/pipeline:${{ github.sha }}
```

Use environment protection rules and required reviews before deploying to production.

## Observability, Monitoring, & Logging

- Logs: structured JSON logging from the Python services. Route to a central logging service (CloudWatch, Datadog, ELK).
- Metrics: expose Prometheus metrics for:
  - processed frames / sec
  - tracks active
  - fusion scores distribution
  - alerts/sec
  - model inference latency
- Tracing: instrument critical paths with OpenTelemetry for request/processing traces.
- Health checks: implement `/live` and `/ready` endpoints used by orchestrators.
- Alerting: integrate with PagerDuty/Slack for high-priority failures (e.g., processing down, DB unavailable).

## Security & Privacy

- Secrets: store in cloud secret manager; never store service keys in repository.
- Data minimization: store only necessary crops and metadata; mask PII in logs.
- Access control: restrict Supabase and object store write access to backend service identities.
- Network segmentation: restrict camera streams to private subnets where possible.
- Encryption: enable TLS for all inbound/outbound traffic and at-rest encryption for DB and object stores.
- Secure dependencies: run dependency scanning (Dependabot, Snyk) and periodic updates.

## Testing Strategy

- Unit tests: module-level tests already present; run in CI.
- Integration tests: small test-suite that runs detection -> tracking -> fusion on a short recorded video.
- Smoke tests: container-level smoke tests that assert the Flask API and `/api/state` respond.
- Performance tests: run on dedicated hardware with representative video to measure throughput.

## Performance & Scaling

- For scale, separate processing into: capture/ingest, inference worker(s), and API/frontend.
- GPU scaling: run inference workers on GPU nodes and use a queue (Redis, SQS) to feed frames.
- Autoscaling: scale inference replicas based on queue length or custom inference latency metrics.
- Batching: if acceptable, batch small sets of frames for more efficient GPU utilization.

## Backup & Disaster Recovery

- Back up DB nightly; retain 30 days by default.
- Retain alert crops and artifacts per organizational policy (e.g., 7–30 days), and auto-prune.
- Use multi-AZ DB deployments for resilience.

## Troubleshooting Guide

- `runtime/logs/` contains process logs — inspect for exception traces.
- `runtime/artifacts/latest_pipeline_output.json` shows last JSON payload for dashboard.
- Common issues:
  - Model file not found: confirm path in `project_paths.py` or mounted volume.
  - Supabase schema mismatch: run migrations or reconcile queries.
  - Camera connectivity: test RTSP with `ffplay`.

## Upgrade & Migration Plan

- Rolling deployments with readiness probes to avoid downtime.
- DB migrations: use versioned migration system (e.g., Flyway, Alembic). Add migration tests in CI.
- Model updates: stage new weights in staging environment; compare metrics before roll-forward.

## Compliance & Legal

- If used in privacy-sensitive jurisdictions, consult legal for face-processing rules; consider adding opt-out and retention policies.
- Log consent and data processing purposes. Keep audit trail for access to stored images.

## Operational Playbook (Checklist)

Before production cutover:
- [ ] Reconcile Supabase migrations and code queries
- [ ] Ensure secrets are in secret manager
- [ ] Build container images and verify on staging
- [ ] Run smoke and integration tests
- [ ] Configure monitoring and alerting thresholds
- [ ] Document retention and access policies

Runbook examples:
- Restart backend service: `kubectl rollout restart deployment/pipeline-backend`
- Flush and re-index embeddings: run `facial_recognition_module/entrypoint/reindex.py` (implement as needed)

## Roadmap & Future Work

- Add authentication/role-based access to the dashboard
- Add model hot-swap support for zero-downtime model updates
- Support multi-camera distributed ingestion (edge devices + central inference)
- Add a lightweight mobile app for alert consumption and push notifications
- Harden Supabase schema and replace inconsistent columns

## Appendix

- Code entrypoints: `run_surveillance_pipeline.py`, `surveillance_live_service.py`.
- Docs: `AGENTS.md`, `pipeline.md` (high-level design)
- Runtime artifacts: `runtime/` directory

Contact / ownership
- Primary owner: Engineering Team
- Secondary owner: DevOps

---

This document should be reviewed with stakeholders and updated as you implement infra and schema changes. For next steps I can:
- produce a `docker-compose.yml` and `Dockerfile` draft
- add a GitHub Actions pipeline example file
- reconcile Supabase schema migrations with the code

Tell me which next step you want me to do.
