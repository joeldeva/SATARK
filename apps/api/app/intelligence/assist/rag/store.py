"""Bucket-aware vector persistence for the assist lane.

Primary backend is Chroma.  When Chroma is not installed (offline demo box, CI)
we fall back to a small persisted in-process vector store (cosine over a JSONL
file per bucket under ``CHROMA_DIR``) so ingest/query keep working AND persist
across restarts.  Either way embeddings come from the shared assist embedding
provider, never from the verdict lane.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import settings
from app.intelligence.assist.rag.embeddings import backend as embed_backend
from app.intelligence.assist.rag.embeddings import embed, embed_one

logger = logging.getLogger(__name__)

_VALID_BUCKETS = {"survey_generation", "validation", "general", "question_bank"}
_LOCK = threading.Lock()
_LOCAL_COLLECTIONS: dict[str, "_LocalCollection"] = {}


def _bucket_name(bucket: str) -> str:
    bucket = (bucket or "general").strip().lower()
    return bucket if bucket in _VALID_BUCKETS else "general"


# ───────────────────────── Chroma backend ────────────────────────────────

def chroma_client():
    try:
        import chromadb
    except Exception as exc:  # noqa: BLE001
        logger.debug("Chroma package unavailable, using local vector store: %s", exc)
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
        logger.warning("Chroma client init failed, using local vector store: %s", exc)
        return None


# ───────────────────────── local fallback backend ────────────────────────

class _LocalCollection:
    """Persisted cosine vector store: one JSONL file per bucket."""

    def __init__(self, name: str):
        self.name = name
        os.makedirs(settings.CHROMA_DIR, exist_ok=True)
        self.path = Path(settings.CHROMA_DIR) / f"{name}.jsonl"
        self._rows: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                self._rows[row["id"]] = row
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local vector store load failed for %s: %s", self.name, exc)

    def _persist(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            for row in self._rows.values():
                handle.write(json.dumps(row, default=str) + "\n")

    def upsert(self, documents, embeddings, metadatas, ids):
        for doc, vec, meta, _id in zip(documents, embeddings, metadatas, ids):
            self._rows[_id] = {"id": _id, "text": doc, "embedding": list(vec), "metadata": meta or {}}
        self._persist()

    def query(self, query_embeddings, n_results=5):
        q = query_embeddings[0]
        scored = []
        for row in self._rows.values():
            scored.append((_cosine(q, row["embedding"]), row))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: max(1, int(n_results))]
        return {
            "documents": [[row["text"] for _, row in top]],
            "metadatas": [[row["metadata"] for _, row in top]],
            "ids": [[row["id"] for _, row in top]],
            # store cosine similarity as a distance (1 - sim) to match Chroma shape
            "distances": [[round(1.0 - score, 6) for score, _ in top]],
        }

    def count(self) -> int:
        return len(self._rows)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def get_collection(bucket: str):
    name = f"satark_{_bucket_name(bucket)}"
    client = chroma_client()
    if client is not None:
        try:
            return client.get_or_create_collection(name=name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_or_create_collection(%s) failed: %s", name, exc)
    with _LOCK:
        if name not in _LOCAL_COLLECTIONS:
            _LOCAL_COLLECTIONS[name] = _LocalCollection(name)
        return _LOCAL_COLLECTIONS[name]


# ───────────────────────── public API ────────────────────────────────────

def upsert_chunks(
    bucket: str,
    chunks: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    ids: Optional[List[str]] = None,
    source_id: Optional[str] = None,
) -> int:
    if not chunks:
        return 0
    bucket_key = _bucket_name(bucket)
    metadatas = metadatas or [{} for _ in chunks]
    ids = ids or [f"{source_id or 'doc'}-{i}" for i in range(len(chunks))]
    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Vector store unavailable; cannot ingest knowledge sources")
    try:
        collection.upsert(
            documents=chunks,
            embeddings=embed(chunks),
            metadatas=metadatas,
            ids=ids,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Vector upsert failed for bucket '{bucket_key}': {exc}") from exc
    logger.info("ingest bucket=%s chunks=%d backend=%s", bucket_key, len(chunks), embed_backend())
    return len(chunks)


def query(bucket: str, text: str, k: int = 5) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        return []
    bucket_key = _bucket_name(bucket)
    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Vector store unavailable; cannot query knowledge sources")
    try:
        res = collection.query(query_embeddings=[embed_one(text)], n_results=max(1, int(k)))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Vector query failed for bucket '{bucket_key}': {exc}") from exc

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
    mode = "chroma" if client is not None else "local-vector-store"
    buckets = {}
    for bucket in sorted(_VALID_BUCKETS):
        bucket_key = _bucket_name(bucket)
        try:
            coll = get_collection(bucket_key)
            buckets[bucket_key] = {"count": coll.count() if coll else None}
        except Exception:  # noqa: BLE001
            buckets[bucket_key] = {"count": None}
    return {
        "enabled": True,
        "mode": mode,
        "embedding_backend": embed_backend(),
        "url": settings.CHROMA_URL if (settings.CHROMA_URL or "").strip() else None,
        "path": settings.CHROMA_DIR,
        "buckets": buckets,
        "needs_review": True,
        "is_verdict": False,
    }
