"""Bucket-aware Chroma persistence for the assist lane."""

from __future__ import annotations

import logging
import os
import hashlib
import math
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)

_VALID_BUCKETS = {"survey_generation", "validation", "general"}


def _bucket_name(bucket: str) -> str:
    bucket = (bucket or "general").strip().lower()
    return bucket if bucket in _VALID_BUCKETS else "general"


def _embed_text(text: str, dimensions: int = 64) -> list[float]:
    """Create a deterministic local embedding without downloading a model."""

    vector = [0.0] * dimensions
    for token in re.findall(r"\b[\w-]{2,}\b", (text or "").lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


def chroma_client():
    try:
        import chromadb
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma package unavailable: %s", exc)
        return None
    configured_url = (settings.CHROMA_URL or "").strip()
    try:
        if configured_url:
            parsed = urlparse(configured_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            return chromadb.HttpClient(host=host, port=port, ssl=parsed.scheme == "https")
        os.makedirs(settings.CHROMA_DIR, exist_ok=True)
        return chromadb.PersistentClient(path=settings.CHROMA_DIR)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma client init failed: %s", exc)
        return None


def get_collection(bucket: str):
    client = chroma_client()
    if not client:
        return None
    name = f"satark_{_bucket_name(bucket)}"
    try:
        return client.get_or_create_collection(name=name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_or_create_collection(%s) failed: %s", name, exc)
        return None


def upsert_chunks(
    bucket: str,
    chunks: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    ids: Optional[List[str]] = None,
    source_id: Optional[str] = None,
) -> int:
    """Upsert chunks to Chroma. Raises when Chroma is unavailable."""

    if not chunks:
        return 0
    bucket_key = _bucket_name(bucket)
    metadatas = metadatas or [{} for _ in chunks]
    ids = ids or [f"{source_id or 'doc'}-{i}" for i in range(len(chunks))]

    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Chroma is not available; cannot ingest knowledge sources")
    try:
        collection.upsert(
            documents=chunks,
            embeddings=[_embed_text(chunk) for chunk in chunks],
            metadatas=metadatas,
            ids=ids,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Chroma upsert failed for bucket '{bucket_key}': {exc}") from exc
    return len(chunks)


def query(bucket: str, text: str, k: int = 5) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        return []
    bucket_key = _bucket_name(bucket)
    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Chroma is not available; cannot query knowledge sources")
    try:
        res = collection.query(query_embeddings=[_embed_text(text)], n_results=max(1, int(k)))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Chroma query failed for bucket '{bucket_key}': {exc}") from exc

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0] or [{}] * len(docs)
    ids = (res.get("ids") or [[]])[0] or [f"r{i}" for i in range(len(docs))]
    distances = (res.get("distances") or [[]])[0] or [0.0] * len(docs)
    out = []
    for i, doc in enumerate(docs):
        score = 1.0 - float(distances[i] or 0.0)
        out.append({
            "id": ids[i],
            "text": doc,
            "metadata": metas[i] if i < len(metas) else {},
            "score": round(score, 4),
        })
    return out


def status() -> dict:
    client = chroma_client()
    enabled = client is not None
    buckets = {}
    for bucket in sorted(_VALID_BUCKETS):
        bucket_key = _bucket_name(bucket)
        if enabled:
            try:
                coll = client.get_or_create_collection(name=f"satark_{bucket_key}")
                buckets[bucket_key] = {"chroma_count": coll.count()}
            except Exception:  # noqa: BLE001
                buckets[bucket_key] = {"chroma_count": None}
        else:
            buckets[bucket_key] = {"chroma_count": None}
    return {
        "enabled": enabled,
        "mode": "http" if (settings.CHROMA_URL or "").strip() else "persistent",
        "url": settings.CHROMA_URL if (settings.CHROMA_URL or "").strip() else None,
        "path": settings.CHROMA_DIR,
        "buckets": buckets,
        "needs_review": True,
        "is_verdict": False,
    }
