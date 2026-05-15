from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CACHE_DIR = ROOT_DIR / ".cache"
RUNTIME_DIR = ROOT_DIR / "runtime"
ARTIFACTS_DIR = RUNTIME_DIR / "artifacts"
ALERTS_DIR = ARTIFACTS_DIR / "alerts"
LOGS_DIR = RUNTIME_DIR / "logs"

for directory in (CACHE_DIR, RUNTIME_DIR, ARTIFACTS_DIR, ALERTS_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
