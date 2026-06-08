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


def test_frontend_role_flow_contracts():
    client = _client()

    login = client.post("/api/auth/login", json={"username": "sdrd", "password": "design123"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "sdrd"

    generated = client.post(
        "/api/surveys/generate",
        json={"prompt": "Generate a household employment survey for urban demolition impact", "user_id": "sdrd"},
    )
    assert generated.status_code == 200
    assert generated.json()["survey"]["metadata"]["assist"]["is_verdict"] is False
    assert generated.json()["survey"]["metadata"]["assist"]["needs_review"] is True

    genuine = client.post(
        "/api/responses",
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

    flagged = client.get("/api/responses?status=flagged")
    assert flagged.status_code == 200
    assert any(item["id"] == suspicious.json()["responseId"] for item in flagged.json()["responses"])

    review = client.post("/api/coding/review", json={"responseId": suspicious.json()["responseId"], "approved": False})
    assert review.status_code == 200
    assert review.json()["ok"] is True

    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["totalResponses"] >= 2
    assert analytics.json()["flagged"] >= 1
