from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        survey_id = f"flow-generated-{uuid4().hex[:8]}"
        return {
            "survey_id": survey_id,
            "title": "Flow Generated Survey",
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
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_frontend_role_flow_contracts(monkeypatch):
    client = _client()

    import services.response_service as response_service

    original_store = response_service.store_collection_response

    def store_without_redis(db, payload):
        return original_store(db, payload, event_publisher=lambda events, event_payload: events)

    monkeypatch.setattr(response_service, "store_collection_response", store_without_redis)

    sdrd_headers = _token(client, "sdrd", "design123")
    fod_headers = _token(client, "fod", "field123")
    dpd_headers = _token(client, "dpd", "process123")
    scd_headers = _token(client, "scd", "coord123")

    generated = client.post(
        "/api/surveys/generate",
        headers=sdrd_headers,
        json={"prompt": "Generate a household employment survey for urban demolition impact", "user_id": "sdrd"},
    )
    assert generated.status_code == 200
    assert generated.json()["survey"]["metadata"]["assist"]["is_verdict"] is False
    assert generated.json()["survey"]["metadata"]["assist"]["needs_review"] is True

    genuine = client.post(
        "/api/responses",
        headers=fod_headers,
        json={
            "surveyId": "emp-2026",
            "householdId": "HH-TN-0042",
            "enumeratorId": "ENUM-A",
            "answers": {"age": "34", "occupation": "Salaried", "employer": "Private", "income": "25000", "household": "4"},
            "speedMode": "normal",
            "elapsedSeconds": 90,
        },
    )
    assert genuine.status_code == 200
    assert genuine.json()["trustLevel"] == "Green"

    suspicious = client.post(
        "/api/responses",
        headers=fod_headers,
        json={
            "surveyId": "emp-2026",
            "householdId": "HH-TN-0042",
            "enumeratorId": "ENUM-B",
            "answers": {
                "age": "34",
                "occupation": "Unemployed",
                "income": "200000",
                "q1": "99",
                "q2": "99",
                "q3": "99",
                "q4": "99",
            },
            "speedMode": "too-fast",
            "elapsedSeconds": 4,
        },
    )
    assert suspicious.status_code == 200
    assert suspicious.json()["trustLevel"] == "Red"

    flagged = client.get("/api/responses?status=flagged", headers=dpd_headers)
    assert flagged.status_code == 200
    assert any(item["id"] == suspicious.json()["responseId"] for item in flagged.json()["responses"])

    review = client.post(
        "/api/coding/review",
        headers=dpd_headers,
        json={"responseId": suspicious.json()["responseId"], "approved": False},
    )
    assert review.status_code == 200
    assert review.json()["ok"] is True

    rejected = client.post(
        "/api/coding/review",
        headers=sdrd_headers,
        json={"responseId": suspicious.json()["responseId"], "approved": False},
    )
    assert rejected.status_code == 403

    analytics = client.get("/api/analytics", headers=scd_headers)
    assert analytics.status_code == 200
    assert analytics.json()["totalResponses"] >= 2
    assert analytics.json()["flagged"] >= 1
