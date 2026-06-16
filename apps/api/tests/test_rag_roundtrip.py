"""RAG ingest -> query roundtrip and question-bank semantic search.

Uses the persisted local vector store (no Chroma / no network needed). The
embedding is the offline lexical-semantic fallback; in production the neural
model is swapped in via RAG_EMBEDDINGS=st.
"""
import importlib

import pytest

from app.config import settings


@pytest.fixture()
def fresh_store(tmp_path, monkeypatch):
    # isolate the vector store to a temp dir and reset cached state
    monkeypatch.setattr(settings, "CHROMA_DIR", str(tmp_path / "vec"))
    monkeypatch.setattr(settings, "CHROMA_URL", "")
    import app.intelligence.assist.rag.store as store

    importlib.reload(store)
    import services.question_bank as qb

    importlib.reload(qb)
    yield store, qb


def test_rag_ingest_then_query_returns_new_document(fresh_store):
    store, _qb = fresh_store
    from app.intelligence.assist.rag.ingest import ingest_bytes
    from app.intelligence.assist.rag.service import answer

    doc = (
        "Fisheries household income survey module.\n\n"
        "Question 1: What is the monthly income of the fisheries household from fishing?\n\n"
        "Question 2: How many members of the fisheries household earn an income from fishing?\n\n"
        "Question 3: Does the fisheries household have any income source other than fishing?\n"
    )
    info = ingest_bytes(bucket="survey_generation", filename="fisheries.txt", data=doc.encode("utf-8"))
    assert info["chunk_count"] >= 1

    result = answer(question="fisheries income questions", bucket="survey_generation", k=5)
    assert result["sources"], "query must return the ingested document"
    filenames = [(s.get("metadata") or {}).get("filename") for s in result["sources"]]
    assert "fisheries.txt" in filenames


def test_question_bank_semantic_search_ranks_paraphrase_top3(fresh_store):
    _store, qb = fresh_store
    added = qb.add({"text": "What is your monthly household expenditure?", "tags": ["expenditure", "household"]})

    results = qb.search("spending per month", k=3)
    ids = [r.get("id") for r in results]
    assert added["id"] in ids, f"paraphrase 'spending per month' should rank the expenditure question top-3, got {ids}"


def test_question_bank_returns_all_without_query(fresh_store):
    _store, qb = fresh_store
    everything = qb.all_questions()
    assert len(everything) >= 1
