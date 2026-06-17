"""Bucket-aware vector persistence for the assist lane.

Backends:
- postgres: cloud-friendly storage in the main database.
- chroma: local/server Chroma when explicitly configured.
- local: persisted JSONL fallback for SQLite/offline development.

Embeddings always come from the assist embedding provider. The verdict lane does
not import this module.
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
_POSTGRES_COLLECTIONS: dict[str, "_PostgresCollection"] = {}


def _bucket_name(bucket: str) -> str:
    bucket = (bucket or "general").strip().lower()
    return bucket if bucket in _VALID_BUCKETS else "general"


def _selected_backend() -> str:
    configured = (settings.VECTOR_STORE or "auto").strip().lower()
    if configured in {"postgres", "chroma", "local"}:
        return configured
    if (settings.CHROMA_URL or "").strip():
        return "chroma"
    if not settings.DATABASE_URL.startswith("sqlite"):
        return "postgres"
    return "local"


# Chroma backend

def chroma_client():
    if _selected_backend() != "chroma":
        return None
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


# Postgres backend

class _PostgresCollection:
    """Small cosine-search vector store backed by ``rag_chunks``.

    This avoids a separate vector database on free hosting. It is enough for the
    demo-sized source bank and keeps provenance metadata in the same database as
    surveys, responses, validation rows, and audit logs.
    """

    def __init__(self, bucket: str):
        self.bucket = bucket

    def upsert(self, documents, embeddings, metadatas, ids):
        from app.database import SessionLocal
        from models.platform import RagChunk

        db = SessionLocal()
        try:
            for doc, vec, meta, chunk_id in zip(documents, embeddings, metadatas, ids):
                metadata = dict(meta or {})
                row = (
                    db.query(RagChunk)
                    .filter(RagChunk.bucket == self.bucket, RagChunk.chunk_id == str(chunk_id))
                    .one_or_none()
                )
                source_id = (
                    metadata.get("source_id")
                    or metadata.get("source_document")
                    or metadata.get("source")
                    or metadata.get("document")
                )
                if row is None:
                    row = RagChunk(bucket=self.bucket, chunk_id=str(chunk_id))
                    db.add(row)
                row.text = str(doc)
                row.embedding = [float(item) for item in (vec or [])]
                row.metadata_json = metadata
                row.source_id = str(source_id) if source_id else None
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def query(self, query_embeddings, n_results=5):
        from app.database import SessionLocal
        from models.platform import RagChunk

        q = query_embeddings[0] if query_embeddings else []
        db = SessionLocal()
        try:
            rows = db.query(RagChunk).filter(RagChunk.bucket == self.bucket).all()
            scored = []
            for row in rows:
                scored.append((_cosine(q, row.embedding or []), row))
            scored.sort(key=lambda item: item[0], reverse=True)
            top = scored[: max(1, int(n_results))]
            return {
                "documents": [[row.text for _, row in top]],
                "metadatas": [[row.metadata_json or {} for _, row in top]],
                "ids": [[row.chunk_id for _, row in top]],
                "distances": [[round(1.0 - score, 6) for score, _ in top]],
            }
        finally:
            db.close()

    def count(self) -> int:
        from app.database import SessionLocal
        from models.platform import RagChunk

        db = SessionLocal()
        try:
            return db.query(RagChunk).filter(RagChunk.bucket == self.bucket).count()
        finally:
            db.close()


# Local fallback backend

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
        for doc, vec, meta, chunk_id in zip(documents, embeddings, metadatas, ids):
            self._rows[str(chunk_id)] = {
                "id": str(chunk_id),
                "text": doc,
                "embedding": [float(item) for item in (vec or [])],
                "metadata": meta or {},
            }
        self._persist()

    def query(self, query_embeddings, n_results=5):
        q = query_embeddings[0] if query_embeddings else []
        scored = []
        for row in self._rows.values():
            scored.append((_cosine(q, row["embedding"]), row))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: max(1, int(n_results))]
        return {
            "documents": [[row["text"] for _, row in top]],
            "metadatas": [[row["metadata"] for _, row in top]],
            "ids": [[row["id"] for _, row in top]],
            "distances": [[round(1.0 - score, 6) for score, _ in top]],
        }

    def count(self) -> int:
        return len(self._rows)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    na = math.sqrt(sum(float(x) * float(x) for x in a[:n]))
    nb = math.sqrt(sum(float(x) * float(x) for x in b[:n]))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def get_collection(bucket: str):
    bucket_key = _bucket_name(bucket)
    backend = _selected_backend()
    if backend == "postgres":
        with _LOCK:
            if bucket_key not in _POSTGRES_COLLECTIONS:
                _POSTGRES_COLLECTIONS[bucket_key] = _PostgresCollection(bucket_key)
            return _POSTGRES_COLLECTIONS[bucket_key]

    if backend == "chroma":
        name = f"satark_{bucket_key}"
        client = chroma_client()
        if client is not None:
            try:
                return client.get_or_create_collection(name=name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("get_or_create_collection(%s) failed: %s", name, exc)

    name = f"satark_{bucket_key}"
    with _LOCK:
        if name not in _LOCAL_COLLECTIONS:
            _LOCAL_COLLECTIONS[name] = _LocalCollection(name)
        return _LOCAL_COLLECTIONS[name]


# Public API

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
    logger.info(
        "ingest bucket=%s chunks=%d vector_store=%s embedding=%s",
        bucket_key,
        len(chunks),
        _selected_backend(),
        embed_backend(),
    )
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
    requested = _selected_backend()
    client = chroma_client() if requested == "chroma" else None
    mode = "chroma" if client is not None else requested
    if requested == "chroma" and client is None:
        mode = "local-vector-store"
    buckets = {}
    for bucket in sorted(_VALID_BUCKETS):
        bucket_key = _bucket_name(bucket)
        try:
            coll = get_collection(bucket_key)
            buckets[bucket_key] = {"count": coll.count() if coll else None}
        except Exception as exc:  # noqa: BLE001
            buckets[bucket_key] = {"count": None, "error": str(exc)}
    return {
        "enabled": True,
        "mode": mode,
        "requested_backend": requested,
        "embedding_backend": embed_backend(),
        "url": settings.CHROMA_URL if (settings.CHROMA_URL or "").strip() and requested == "chroma" else None,
        "path": settings.CHROMA_DIR if mode == "local-vector-store" else None,
        "buckets": buckets,
        "needs_review": True,
        "is_verdict": False,
    }
