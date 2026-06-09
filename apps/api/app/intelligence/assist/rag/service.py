"""RAG service: retrieval -> reranker -> local summary, always assist-only.

Every output carries ``is_verdict=False`` and ``needs_review=True``. This module
is the assist surface for ``POST /api/rag/query`` and the bucket-scoped grounded
answer the SDRD AI Assist panel will render.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.intelligence.assist.rag.store import query as store_query
from app.intelligence.assist.rag.store import status as store_status

logger = logging.getLogger(__name__)

_VALID_BUCKETS = {"survey_generation", "validation", "general"}


def _normalize_bucket(bucket: str | None) -> str:
    b = (bucket or "general").strip().lower()
    return b if b in _VALID_BUCKETS else "general"


def _rerank(question: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simple keyword-overlap rerank — cheap, deterministic, no model dep."""
    q_tokens = set(re.findall(r"\b[a-z0-9_]{3,}\b", (question or "").lower()))
    if not q_tokens or not hits:
        return hits

    def boost(hit: Dict[str, Any]) -> float:
        text = (hit.get("text") or "")
        tokens = set(re.findall(r"\b[a-z0-9_]{3,}\b", text.lower()))
        if not tokens:
            return 0.0
        return len(q_tokens & tokens) / max(len(q_tokens), 1)

    reranked = []
    for hit in hits:
        h = dict(hit)
        h["score"] = round((h.get("score") or 0.0) * 0.6 + boost(h) * 0.4, 4)
        reranked.append(h)
    reranked.sort(key=lambda x: x.get("score") or 0.0, reverse=True)
    return reranked


def answer(question: str, bucket: str = "general", k: int = 5) -> Dict[str, Any]:
    """Return a grounded assist answer for ``question`` within ``bucket``."""
    bucket_key = _normalize_bucket(bucket)
    raw_hits = store_query(bucket_key, question or "", k=max(1, int(k)))
    hits = _rerank(question or "", raw_hits)

    sources = [
        {
            "id": hit.get("id"),
            "score": hit.get("score"),
            "snippet": _snippet(hit.get("text") or ""),
            "metadata": hit.get("metadata") or {},
        }
        for hit in hits
    ]

    # Compose a grounded summary from top sources. If Chroma is down,
    # store_query raises and the API returns 503.
    summary = ""
    if hits:
        joined = "\n---\n".join(hit.get("text") or "" for hit in hits[:3])
        summary = _summarize_locally(question or "", joined)

    confidence = round(min(1.0, sum(h.get("score") or 0.0 for h in hits[:3]) / 3), 4) if hits else 0.0

    return {
        "question": question,
        "bucket": bucket_key,
        "answer": summary or "No grounded answer available for this bucket yet — try ingesting reference material first.",
        "sources": sources,
        "confidence": confidence,
        "store": store_status(),
        "needs_review": True,
        "is_verdict": False,
    }


def classify_code(text: str, code_type: Optional[str] = None, k: int = 5) -> Dict[str, Any]:
    """Retrieval-only code classification (assist).

    Searches the ``survey_generation`` bucket for ingested code-list entries and
    returns ranked matches. SDRD shows these as 'suggested', never 'approved'.
    """
    hits = store_query("survey_generation", f"{code_type or ''} {text or ''}".strip(), k=max(1, int(k)))
    matches = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        matches.append({
            "code": meta.get("code"),
            "label": meta.get("label") or _snippet(hit.get("text") or ""),
            "type": meta.get("type") or code_type,
            "score": hit.get("score"),
            "source": meta.get("source") or "rag",
        })
    return {
        "text": text,
        "type": code_type,
        "matches": matches,
        "needs_review": True,
        "is_verdict": False,
    }


def _snippet(text: str, max_chars: int = 240) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _summarize_locally(question: str, joined: str) -> str:
    """Tiny extractive summary: return the first sentence per top source."""
    sentences = re.split(r"(?<=[.!?])\s+", joined.strip())
    picks: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        s = sentence.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        picks.append(s)
        if len(picks) >= 3:
            break
    return " ".join(picks)


# Back-compat alias
def answer_from_local_sources(question: str, sources: list[str] | None = None) -> dict:
    return answer(question=question, bucket="general")
