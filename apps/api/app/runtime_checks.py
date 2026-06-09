from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.intelligence.assist.rag.store import status as chroma_status
from services.events import RedisPublishError


class RuntimeCheckError(RuntimeError):
    """Raised when a required runtime dependency is unavailable."""


def check_database_schema() -> dict[str, Any]:
    if settings.DATABASE_URL.startswith("sqlite"):
        return {"ok": True, "database": "sqlite-test", "migration": "not-required-for-test-db"}

    expected = _alembic_head()
    with engine.connect() as connection:
        actual = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if actual != expected:
        raise RuntimeCheckError(f"Database migration mismatch: current={actual!r}, expected={expected!r}")
    return {"ok": True, "database": "postgres", "migration": actual}


def check_redis() -> dict[str, Any]:
    try:
        import redis
    except Exception as exc:  # noqa: BLE001
        raise RuntimeCheckError(f"Redis package is unavailable: {exc}") from exc
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeCheckError(f"Redis is unreachable at {settings.REDIS_URL}: {exc}") from exc
    return {"ok": True, "url": settings.REDIS_URL}


def check_chroma() -> dict[str, Any]:
    status = chroma_status()
    if not status["enabled"]:
        raise RuntimeCheckError("Chroma is unavailable")
    return {"ok": True, "mode": status["mode"], "url": status["url"], "path": status["path"]}


def check_ollama() -> dict[str, Any]:
    if settings.LLM_PROVIDER.lower() != "ollama":
        raise RuntimeCheckError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        response = httpx.get(url, timeout=3)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeCheckError(f"Ollama is unreachable at {settings.OLLAMA_BASE_URL}: {exc}") from exc
    models = response.json().get("models") or []
    names = {item.get("name") for item in models}
    if settings.LLM_REQUIRED and settings.LLM_MODEL not in names:
        raise RuntimeCheckError(f"Required Ollama model '{settings.LLM_MODEL}' is not pulled")
    return {"ok": True, "model": settings.LLM_MODEL, "base_url": settings.OLLAMA_BASE_URL}


def readiness() -> dict[str, Any]:
    checks = {
        "database": check_database_schema,
        "redis": check_redis,
        "chroma": check_chroma,
        "ollama": check_ollama,
    }
    result: dict[str, Any] = {"ready": True, "checks": {}}
    for name, check in checks.items():
        try:
            result["checks"][name] = check()
        except Exception as exc:  # noqa: BLE001
            result["ready"] = False
            result["checks"][name] = {"ok": False, "error": str(exc)}
    return result


def assert_required_runtime() -> None:
    db = check_database_schema()
    if db["database"] != "postgres":
        return
    check_redis()
    check_chroma()
    check_ollama()


def _alembic_head() -> str:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(config_path.parent / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()
