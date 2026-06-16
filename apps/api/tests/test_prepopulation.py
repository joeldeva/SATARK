"""Prepopulation via a MOCK government-ID registry (demo pattern, not e-KYC)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from models.platform import Response
from services.response_service import store_collection_response


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        return {"survey_id": "x", "title": "x", "questions": [], "metadata": {"assist": {"is_verdict": False}}}


def _client() -> TestClient:
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()
    set_db_dependency(get_db)
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _headers(client):
    r = client.post("/api/auth/login", json={"username": "fod", "password": "field123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_prepopulate_match_returns_record_and_demo_badge():
    client = _client()
    headers = _headers(client)
    # any well-formed Aadhaar ending 4242 matches the mock record (no checksum)
    r = client.post("/api/prepopulate", headers=headers, json={"id_type": "aadhaar", "id_number": "1234-5678-4242"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] is True
    assert body["fields"]["name"] == "Lakshmi R"
    assert body["fields"]["occupation"] == "Salaried"
    assert body["tag"] == "From household record"
    assert "no real Aadhaar/UIDAI integration" in body["demo_badge"]
    assert body["is_verdict"] is False


def test_prepopulate_no_match_proceeds_blank_no_error():
    client = _client()
    headers = _headers(client)
    r = client.post("/api/prepopulate", headers=headers, json={"id_type": "aadhaar", "id_number": "0000-0000-0001"})
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] is False
    assert body["fields"] == {}
    assert "no real Aadhaar/UIDAI integration" in body["demo_badge"]


def test_override_prepop_stores_original_and_fires_cross_field():
    client = _client()  # seeds emp-2026 + rules + reference
    db = next(get_db())
    try:
        result = store_collection_response(
            db,
            {
                "surveyId": "emp-2026",
                # prepop said Salaried; enumerator overrode it to Unemployed + high income
                "prepopulated": {"occupation": "Salaried", "name": "Lakshmi R"},
                "answers": {"occupation": "Unemployed", "income": 200000, "age": 34},
                "channel": "web",
            },
            event_publisher=lambda events, payload: events,
        )
        # cross-field FIRES because the overridden occupation contradicts the income
        cross = next(layer for layer in result["intelligence"]["layers"] if layer["layer"] == "Cross-field")
        assert cross["status"] == "fail"
        assert "contradicts" in cross["reason"].lower()
        assert result["trustLevel"] in {"Amber", "Red"}
        # the original prepop value is preserved on the stored response
        stored = db.get(Response, result["responseId"])
        assert stored.prepopulated == {"occupation": "Salaried", "name": "Lakshmi R"}
    finally:
        db.close()
