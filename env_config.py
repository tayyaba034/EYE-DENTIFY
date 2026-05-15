from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_project_env() -> Path:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path, override=False)
    return env_path


def get_env(name: str, default: str = "") -> str:
    load_project_env()
    return os.getenv(name, default)
