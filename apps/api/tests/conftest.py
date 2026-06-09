from __future__ import annotations

import os
from pathlib import Path


def pytest_configure():
    root = Path(__file__).resolve().parents[3]
    db_path = root / "data" / "test_satark.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["LLM_REQUIRED"] = "false"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"
