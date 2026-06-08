from __future__ import annotations

from app.intelligence.assist.rag.store import status as store_status


def answer_from_local_sources(question: str, sources: list[str] | None = None) -> dict:
    return {
        "question": question,
        "answer": "Grounded assist answer requires an ingested local Chroma collection.",
        "sources": sources or [],
        "confidence": 0,
        "store": store_status(),
        "needs_review": True,
        "is_verdict": False,
    }
