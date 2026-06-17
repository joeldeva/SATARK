from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.intelligence.assist.rag.store import status as vector_status


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
        raise RuntimeCheckError(f"Redis is unreachable at {_redact_url(settings.REDIS_URL)}: {exc}") from exc
    return {"ok": True, "url": _redact_url(settings.REDIS_URL)}


def check_vector_store() -> dict[str, Any]:
    status = vector_status()
    requested = status.get("requested_backend") or status.get("mode")
    if requested == "postgres":
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM rag_chunks LIMIT 1"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeCheckError(f"Postgres RAG table is unavailable: {exc}") from exc
    if requested == "chroma" and status.get("mode") != "chroma" and not settings.DATABASE_URL.startswith("sqlite"):
        raise RuntimeCheckError("Chroma was requested but is unavailable")
    return {
        "ok": True,
        "mode": status.get("mode"),
        "requested_backend": requested,
        "embedding_backend": status.get("embedding_backend"),
        "buckets": status.get("buckets"),
    }


def check_llm() -> dict[str, Any]:
    provider = (settings.LLM_PROVIDER or "none").strip().lower()
    if provider == "none":
        if settings.LLM_REQUIRED:
            raise RuntimeCheckError("LLM_PROVIDER=none but LLM_REQUIRED=true")
        return {"ok": True, "provider": "none", "required": False, "configured": False}

    if provider == "openrouter":
        configured = bool(settings.OPENROUTER_API_KEY)
        if settings.LLM_REQUIRED and not configured:
            raise RuntimeCheckError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        return {
            "ok": True,
            "provider": "openrouter",
            "required": settings.LLM_REQUIRED,
            "configured": configured,
            "model": settings.OPENROUTER_MODEL,
        }

    if provider == "ollama":
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        try:
            response = httpx.get(url, timeout=3)
            response.raise_for_status()
            models = response.json().get("models") or []
        except Exception as exc:  # noqa: BLE001
            if settings.LLM_REQUIRED:
                raise RuntimeCheckError(f"Ollama is unreachable at {settings.OLLAMA_BASE_URL}: {exc}") from exc
            return {
                "ok": True,
                "provider": "ollama",
                "required": False,
                "configured": False,
                "warning": f"Ollama unavailable, deterministic fallback active: {exc}",
            }
        names = {item.get("name") for item in models}
        if settings.LLM_REQUIRED and settings.LLM_MODEL not in names:
            raise RuntimeCheckError(f"Required Ollama model '{settings.LLM_MODEL}' is not pulled")
        return {
            "ok": True,
            "provider": "ollama",
            "required": settings.LLM_REQUIRED,
            "configured": True,
            "model": settings.LLM_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
        }

    if settings.LLM_REQUIRED:
        raise RuntimeCheckError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
    return {
        "ok": True,
        "provider": provider,
        "required": False,
        "configured": False,
        "warning": f"Unsupported LLM_PROVIDER={settings.LLM_PROVIDER}; deterministic fallback active",
    }


def readiness() -> dict[str, Any]:
    checks = {
        "database": check_database_schema,
        "redis": check_redis,
        "vector_store": check_vector_store,
        "llm": check_llm,
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
    check_vector_store()
    check_llm()


def _alembic_head() -> str:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(config_path.parent / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


def _redact_url(value: str) -> str:
    if not value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    if "@" not in rest:
        return f"{scheme}://<redacted>"
    host = rest.rsplit("@", 1)[1]
    return f"{scheme}://<redacted>@{host}"
