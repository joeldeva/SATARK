from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.rag_routes import router as rag_router
from api.rag_routes import set_db_dependency as set_rag_db_dependency
from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from models.survey import GenerationLog, Survey


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        return {
            "survey_id": f"strict-generated-{uuid4().hex[:8]}",
            "title": "Strict Generated Survey",
            "description": prompt,
            "domain": "labour",
            "questions": [
                {
                    "id": "q_income",
                    "type": "number",
                    "text": "Monthly income?",
                    "validation": {"min": 0, "max": 200000},
                }
            ],
            "metadata": {
                "assist": {
                    "needs_review": True,
                    "is_verdict": False,
                    "role": "survey_generation_draft",
                }
            },
        }


def _client() -> TestClient:
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()

    set_db_dependency(get_db)
    set_rag_db_dependency(get_db)
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(rag_router, prefix="/api")
    return TestClient(app)


def _headers(client: TestClient, username: str = "sdrd", password: str = "design123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_generation_endpoints_log_only_until_explicit_create():
    client = _client()
    headers = _headers(client)

    for path in ["/api/surveys/generate", "/api/generate"]:
        before = _counts()
        response = client.post(
            path,
            headers=headers,
            json={"prompt": "Generate a labour survey for displaced urban households"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_verdict"] is False
        assert body["needs_review"] is True

        after = _counts()
        assert after["surveys"] == before["surveys"]
        assert after["generation_logs"] == before["generation_logs"] + 1


def test_rag_query_503_when_vector_store_unavailable(monkeypatch):
    """If NO vector backend is available at all (neither Chroma nor the local
    fallback), the query lane fails closed with 503 — it never fabricates an
    answer."""
    client = _client()
    headers = _headers(client, "admin", "admin123")

    import app.intelligence.assist.rag.store as store

    monkeypatch.setattr(store, "get_collection", lambda bucket: None)
    response = client.post(
        "/api/rag/query",
        headers=headers,
        json={"bucket": "survey_generation", "question": "What code list should I use?"},
    )

    assert response.status_code == 503
    assert "Vector store unavailable" in response.json()["detail"]


def test_sdrd_can_ingest_kb_docs():
    """KB ingestion is part of the SDRD design workflow (survey:write), not admin-only."""
    client = _client()
    headers = _headers(client, "sdrd", "design123")
    res = client.post(
        "/api/rag/ingest",
        headers=headers,
        files={"file": ("kb.txt", b"PLFS labour module reference questions for survey generation.", "text/plain")},
        data={"bucket": "survey_generation"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["chunk_count"] >= 1


def test_rag_query_works_without_chroma_via_local_store():
    """Default path: no Chroma installed -> local persisted vector store answers."""
    client = _client()
    headers = _headers(client, "admin", "admin123")

    ingest = client.post(
        "/api/rag/ingest",
        headers=headers,
        files={"file": ("note.txt", b"COICOP code list for household consumption expenditure.", "text/plain")},
        data={"bucket": "survey_generation"},
    )
    assert ingest.status_code == 200, ingest.text

    response = client.post(
        "/api/rag/query",
        headers=headers,
        json={"bucket": "survey_generation", "question": "household consumption expenditure code list"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_verdict"] is False
    assert body["sources"], "local vector store should return the ingested source"


def _counts() -> dict[str, int]:
    db = next(get_db())
    try:
        return {
            "surveys": db.query(Survey).count(),
            "generation_logs": db.query(GenerationLog).count(),
        }
    finally:
        db.close()
