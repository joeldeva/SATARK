from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.seed import seed_core_data
from models.platform import AuditLog, CodingResult, ConsentRecord, IntelligenceSession, Response


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        return {
            "survey_id": "persisted-endpoint-draft",
            "title": "Persisted Endpoint Draft",
            "domain": "labour",
            "questions": [],
            "metadata": {"assist": {"needs_review": True, "is_verdict": False}},
        }


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


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_collection_review_dashboard_endpoints_persist(monkeypatch):
    import services.response_service as response_service

    original_store = response_service.store_collection_response

    def store_without_redis(db, payload):
        return original_store(db, payload, event_publisher=lambda events, event_payload: events)

    monkeypatch.setattr(response_service, "store_collection_response", store_without_redis)

    client = _client()
    fod = _token(client, "fod", "field123")
    dpd = _token(client, "dpd", "process123")
    scd = _token(client, "scd", "coord123")

    consent = client.post(
        "/api/consent",
        headers=fod,
        json={"surveyId": "emp-2026", "householdId": "HH-TN-0042", "enumeratorId": "ENUM-A", "consented": True},
    )
    assert consent.status_code == 200
    assert consent.json()["consentId"]

    session = client.post(
        "/api/intelligence/sessions",
        headers=fod,
        json={"surveyId": "emp-2026", "householdId": "HH-TN-0042", "enumeratorId": "ENUM-A"},
    )
    assert session.status_code == 200
    assert session.json()["sessionId"]

    response = client.post(
        "/api/responses",
        headers=fod,
        json={
            "surveyId": "emp-2026",
            "householdId": "HH-TN-0042",
            "enumeratorId": "ENUM-A",
            "answers": {"age": "34", "occupation": "Salaried", "income": "25000", "household": "4"},
            "speedMode": "normal",
            "elapsedSeconds": 90,
        },
    )
    assert response.status_code == 200

    assignments = client.get("/api/assignments?survey_id=emp-2026", headers=scd)
    assert assignments.status_code == 200
    assert assignments.json()["assignments"]

    review = client.post(
        "/api/coding/review",
        headers=dpd,
        json={
            "responseId": response.json()["responseId"],
            "field": "occupation",
            "rawText": "software developer",
            "approvedCode": "2511",
            "approvedLabel": "Software developer",
            "approved": True,
        },
    )
    assert review.status_code == 200
    assert review.json()["codingResultId"]

    action = client.post(
        "/api/actions",
        headers=scd,
        json={"action": "reviewed", "entityType": "response", "entityId": response.json()["responseId"], "reason": "Checked"},
    )
    assert action.status_code == 200
    assert action.json()["auditId"]

    exported = client.post("/api/export", headers=scd, json={"format": "csv"})
    assert exported.status_code == 200
    assert response.json()["responseId"] in exported.json()["content"]

    db = SessionLocal()
    try:
        assert db.query(ConsentRecord).count() >= 1
        assert db.query(IntelligenceSession).count() >= 1
        assert db.query(Response).count() >= 1
        assert db.query(CodingResult).count() >= 1
        assert db.query(AuditLog).count() >= 1
    finally:
        db.close()
