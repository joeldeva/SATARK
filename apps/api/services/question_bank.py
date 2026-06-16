"""Question bank with semantic (embedding) search.

GET /api/question-bank?q=<free text> uses embedding search over the
``question_bank`` vector bucket (not SQL LIKE).  Adding a question upserts its
embedding immediately (ingest-on-create), so a new entry is retrievable right
away.  This is assist-only: results are suggestions (is_verdict:false).
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.intelligence.assist.rag.store import query as store_query
from app.intelligence.assist.rag.store import upsert_chunks

logger = logging.getLogger(__name__)

_BUCKET = "question_bank"
_LOCK = threading.Lock()
_REGISTRY: dict[str, dict[str, Any]] = {}
_INDEXED = False


def _bank_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "question_bank" / "question_bank.json"


def _load_seed() -> list[dict[str, Any]]:
    try:
        data = json.loads(_bank_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return data if isinstance(data, list) else data.get("questions", [])


def _text_of(question: dict[str, Any]) -> str:
    text = question.get("text")
    if isinstance(text, dict):
        text = text.get("en") or next(iter(text.values()), "")
    return str(text or question.get("id") or "")


def _searchable(question: dict[str, Any]) -> str:
    parts = [_text_of(question)]
    parts.extend(str(t) for t in (question.get("tags") or []))
    for key in ("domain", "subdomain", "category"):
        if question.get(key):
            parts.append(str(question[key]))
    return " ".join(parts)


def _index_question(question: dict[str, Any]) -> None:
    qid = str(question.get("id"))
    _REGISTRY[qid] = question
    upsert_chunks(
        _BUCKET,
        [_searchable(question)],
        metadatas=[{"qid": qid, "text": _text_of(question), "domain": question.get("domain")}],
        ids=[qid],
    )


def ensure_indexed() -> None:
    global _INDEXED
    with _LOCK:
        if _INDEXED:
            return
        for question in _load_seed():
            if question.get("id"):
                _index_question(question)
        _INDEXED = True


def all_questions() -> list[dict[str, Any]]:
    ensure_indexed()
    return list(_REGISTRY.values())


def add(question: dict[str, Any]) -> dict[str, Any]:
    """Add a question to the bank and upsert its embedding immediately."""
    ensure_indexed()
    if not question.get("id"):
        question = {**question, "id": f"qb-{uuid4().hex[:8]}"}
    if isinstance(question.get("text"), str):
        question = {**question, "text": {"en": question["text"]}}
    _index_question(question)
    return question


def search(q: str, k: int = 5) -> list[dict[str, Any]]:
    """Embedding search over the question bank; returns ranked questions."""
    ensure_indexed()
    hits = store_query(_BUCKET, q or "", k=max(1, int(k)))
    results = []
    for hit in hits:
        qid = (hit.get("metadata") or {}).get("qid") or hit.get("id")
        question = _REGISTRY.get(str(qid))
        if question:
            results.append({**question, "score": hit.get("score")})
    return results
