from __future__ import annotations

from app.config import settings


def chroma_client():
    try:
        import chromadb
    except Exception:  # noqa: BLE001
        return None
    return chromadb.PersistentClient(path=settings.CHROMA_DIR)


def status() -> dict:
    return {
        "enabled": chroma_client() is not None,
        "path": settings.CHROMA_DIR,
        "needs_review": True,
        "is_verdict": False,
    }
