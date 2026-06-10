from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        return {"survey_id": "unused", "title": "Unused", "questions": [], "metadata": {"assist": {"is_verdict": False}}}


def _client(monkeypatch) -> TestClient:
    import services.collection_service as collection_service
    import services.response_service as response_service

    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()

    def store_without_redis(db, payload):
        return response_service.store_collection_response(db, payload, event_publisher=lambda events, event_payload: events)

    monkeypatch.setattr(collection_service, "store_collection_response", store_without_redis)
    set_db_dependency(get_db)
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_collection_session_branches_from_backend(monkeypatch):
    client = _client(monkeypatch)
    headers = _token(client, "fod", "field123")
    assignments = client.get("/api/assignments?survey_id=emp-2026&status=assigned", headers=headers)
    assignment = assignments.json()["assignments"][0]

    started = client.post("/api/collection/sessions/start", headers=headers, json={"assignmentId": assignment["id"], "language": "en"})
    assert started.status_code == 200
    session_id = started.json()["sessionId"]
    assert started.json()["nextQuestionId"] == "name"

    first = client.post(f"/api/collection/sessions/{session_id}/answer", headers=headers, json={"questionId": "name", "value": "Lakshmi R", "elapsedSeconds": 20})
    assert first.status_code == 200
    assert first.json()["nextQuestionId"] == "age"

    second = client.post(f"/api/collection/sessions/{session_id}/answer", headers=headers, json={"questionId": "age", "value": "34", "elapsedSeconds": 20})
    assert second.status_code == 200
    assert second.json()["nextQuestionId"] == "occupation"

    branched = client.post(f"/api/collection/sessions/{session_id}/answer", headers=headers, json={"questionId": "occupation", "value": "Student", "elapsedSeconds": 20})
    assert branched.status_code == 200
    body = branched.json()
    assert body["nextQuestionId"] == "institution"
    assert body["intelligence"]["decision"] == "BRANCH"
    assert "occupation" in body["intelligence"]["reason"].lower()


def test_collection_session_suspicious_verdict_persists_without_drift(monkeypatch):
    client = _client(monkeypatch)
    headers = _token(client, "fod", "field123")
    assignments = client.get("/api/assignments?survey_id=emp-2026&enumerator_id=ENUM-B&status=assigned", headers=headers)
    assignment = assignments.json()["assignments"][0]

    started = client.post("/api/collection/sessions/start", headers=headers, json={"assignmentId": assignment["id"], "language": "en"})
    session_id = started.json()["sessionId"]

    answers = [
        ("name", "Lakshmi R", 20),
        ("age", "34", 20),
        ("occupation", "Unemployed", 20),
        ("unemp_dur", "3", 20),
        ("income", "200000", 4),
        ("household", "4", 4),
    ]
    latest = None
    for question_id, value, elapsed in answers:
        response = client.post(
            f"/api/collection/sessions/{session_id}/answer",
            headers=headers,
            json={"questionId": question_id, "value": value, "elapsedSeconds": elapsed},
        )
        assert response.status_code == 200
        latest = response.json()

    assert latest["complete"] is True
    session_confidence = latest["intelligence"]["confidence"]
    assert latest["intelligence"]["trustLevel"] == "Red"
    assert session_confidence < 50
    reasons = " ".join(latest["intelligence"]["native_trust"]["reasons"]).lower()
    assert "contradicts" in reasons
    assert "median" in reasons or "pace" in reasons

    completed = client.post(f"/api/collection/sessions/{session_id}/complete", headers=headers)
    assert completed.status_code == 200
    stored = completed.json()
    assert stored["trustLevel"] == "Red"
    assert stored["qualityScore"] == session_confidence
    assert stored["intelligence"]["stored"] is True
