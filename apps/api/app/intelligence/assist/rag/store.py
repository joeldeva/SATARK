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
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import settings
from app.intelligence.assist.rag.embeddings import backend as embed_backend
from app.intelligence.assist.rag.embeddings import embed, embed_one

logger = logging.getLogger(__name__)

_VALID_BUCKETS = {"survey_generation", "validation", "general", "question_bank", "volume_1", "volume_2"}
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

    def all_documents(self):
        from app.database import SessionLocal
        from models.platform import RagChunk

        db = SessionLocal()
        try:
            return [
                {
                    "id": row.chunk_id,
                    "text": row.text,
                    "metadata": row.metadata_json or {},
                    "embedding": row.embedding or [],
                }
                for row in db.query(RagChunk).filter(RagChunk.bucket == self.bucket).all()
            ]
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

    def delete_by_source_id(self, source_id: str) -> int:
        from app.database import SessionLocal
        from models.platform import RagChunk

        db = SessionLocal()
        try:
            rows = db.query(RagChunk).filter(RagChunk.bucket == self.bucket, RagChunk.source_id == source_id).all()
            count = len(rows)
            for row in rows:
                db.delete(row)
            db.commit()
            return count
        except Exception:
            db.rollback()
            raise
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

    def all_documents(self):
        return [
            {
                "id": row["id"],
                "text": row["text"],
                "metadata": row.get("metadata") or {},
                "embedding": row.get("embedding") or [],
            }
            for row in self._rows.values()
        ]

    def count(self) -> int:
        return len(self._rows)

    def delete_by_source_id(self, source_id: str) -> int:
        before = len(self._rows)
        self._rows = {
            row_id: row
            for row_id, row in self._rows.items()
            if (row.get("metadata") or {}).get("source_id") != source_id
        }
        deleted = before - len(self._rows)
        if deleted:
            self._persist()
        return deleted


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


def delete_source_chunks(bucket: str, source_id: str) -> int:
    """Delete all chunks for a stable source ID within a bucket."""
    source_id = str(source_id or "").strip()
    if not source_id:
        return 0
    bucket_key = _bucket_name(bucket)
    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Vector store unavailable; cannot delete knowledge source chunks")
    if hasattr(collection, "delete_by_source_id"):
        return int(collection.delete_by_source_id(source_id))
    if hasattr(collection, "delete"):
        try:
            collection.delete(where={"source_id": source_id})
            return 0
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Vector delete failed for bucket '{bucket_key}': {exc}") from exc
    return 0


def query(bucket: str, text: str, k: int = 5) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        return []
    bucket_key = _bucket_name(bucket)
    collection = get_collection(bucket_key)
    if collection is None:
        raise RuntimeError("Vector store unavailable; cannot query knowledge sources")
    try:
        target = max(1, int(k))
        query_embedding = embed_one(text)
        res = collection.query(query_embeddings=[query_embedding], n_results=max(target * 8, 50))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Vector query failed for bucket '{bucket_key}': {exc}") from exc

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0] or [{}] * len(docs)
    ids = (res.get("ids") or [[]])[0] or [f"r{i}" for i in range(len(docs))]
    distances = (res.get("distances") or [[]])[0] or [0.0] * len(docs)
    vector_hits: dict[str, Dict[str, Any]] = {}
    for i, doc in enumerate(docs):
        score = 1.0 - float(distances[i] or 0.0)
        vector_hits[str(ids[i])] = {
            "id": str(ids[i]),
            "text": doc,
            "metadata": metas[i] if i < len(metas) else {},
            "vector_score": max(0.0, min(1.0, score)),
        }

    lexical_candidates = _all_collection_documents(collection)
    lexical_hits = _bm25_rank(text, lexical_candidates, limit=max(target * 8, 50))
    merged: dict[str, Dict[str, Any]] = {}
    for hit in vector_hits.values():
        merged[hit["id"]] = dict(hit)
    for hit in lexical_hits:
        row = merged.setdefault(
            hit["id"],
            {
                "id": hit["id"],
                "text": hit["text"],
                "metadata": hit.get("metadata") or {},
                "vector_score": 0.0,
            },
        )
        row["lexical_score"] = hit["lexical_score"]

    reranked = []
    for hit in merged.values():
        meta = hit.get("metadata") or {}
        vector_score = float(hit.get("vector_score") or 0.0)
        lexical_score = float(hit.get("lexical_score") or 0.0)
        metadata_score = _metadata_score(text, meta)
        rerank_score = _rerank_score(text, hit.get("text") or "", meta)
        final = (0.45 * vector_score) + (0.30 * lexical_score) + (0.15 * rerank_score) + (0.10 * metadata_score)
        reranked.append({
            "id": hit["id"],
            "text": hit.get("text") or "",
            "metadata": meta,
            "score": round(max(0.0, min(1.0, final)), 4),
            "vector_score": round(vector_score, 4),
            "lexical_score": round(lexical_score, 4),
            "rerank_score": round(rerank_score, 4),
            "retrieval_method": "hybrid_vector_bm25_rerank",
        })
    reranked.sort(key=lambda item: item.get("score") or 0.0, reverse=True)
    return reranked[:target]


def _all_collection_documents(collection) -> List[Dict[str, Any]]:
    if hasattr(collection, "all_documents"):
        return collection.all_documents()
    if hasattr(collection, "get"):
        try:
            data = collection.get(include=["documents", "metadatas", "embeddings"])
            ids = data.get("ids") or []
            docs = data.get("documents") or []
            metas = data.get("metadatas") or [{} for _ in docs]
            embeds = data.get("embeddings") or [[] for _ in docs]
            return [
                {
                    "id": str(ids[i] if i < len(ids) else f"doc-{i}"),
                    "text": docs[i],
                    "metadata": metas[i] if i < len(metas) else {},
                    "embedding": embeds[i] if i < len(embeds) else [],
                }
                for i in range(len(docs))
            ]
        except Exception as exc:  # noqa: BLE001
            logger.debug("collection full scan unavailable for hybrid lexical search: %s", exc)
    return []


def _tokens(value: str) -> List[str]:
    return re.findall(r"\b[\w]{2,}\b", (value or "").lower())


def _bm25_rank(query_text: str, rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    if not rows:
        return []
    query_tokens = _tokens(query_text)
    if not query_tokens:
        return []
    docs_tokens = [_tokens(row.get("text") or "") for row in rows]
    avg_len = sum(len(tokens) for tokens in docs_tokens) / max(len(docs_tokens), 1)
    doc_freq: dict[str, int] = {}
    for tokens in docs_tokens:
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1
    n_docs = len(rows)
    k1 = 1.4
    b = 0.72
    raw = []
    for row, tokens in zip(rows, docs_tokens):
        if not tokens:
            continue
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            if token not in tf:
                continue
            idf = math.log(1 + ((n_docs - doc_freq.get(token, 0) + 0.5) / (doc_freq.get(token, 0) + 0.5)))
            denom = tf[token] + k1 * (1 - b + b * (len(tokens) / max(avg_len, 1)))
            score += idf * ((tf[token] * (k1 + 1)) / max(denom, 0.0001))
        if score > 0:
            raw.append((score, row))
    if not raw:
        return []
    max_score = max(score for score, _ in raw) or 1.0
    ranked = []
    for score, row in raw:
        ranked.append({
            "id": str(row.get("id")),
            "text": row.get("text") or "",
            "metadata": row.get("metadata") or {},
            "lexical_score": round(score / max_score, 4),
        })
    ranked.sort(key=lambda item: item["lexical_score"], reverse=True)
    return ranked[:limit]


def _metadata_score(query_text: str, metadata: Dict[str, Any]) -> float:
    if not metadata:
        return 0.0
    query = " ".join(_tokens(query_text))
    fields = " ".join(str(metadata.get(key) or "") for key in ("source_document", "section", "question_id", "language", "filename"))
    if not query or not fields:
        return 0.0
    q = set(_tokens(query))
    m = set(_tokens(fields))
    return len(q & m) / max(len(q), 1)


def _rerank_score(query_text: str, text: str, metadata: Dict[str, Any]) -> float:
    q = set(_tokens(query_text))
    haystack = set(_tokens(" ".join([text, json.dumps(metadata, default=str)])))
    if not q or not haystack:
        return 0.0
    overlap = len(q & haystack) / max(len(q), 1)
    phrase_bonus = 0.15 if query_text.lower() in text.lower() else 0.0
    return min(1.0, overlap + phrase_bonus)


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
        "retrieval_method": "hybrid_vector_bm25_rerank",
    }
