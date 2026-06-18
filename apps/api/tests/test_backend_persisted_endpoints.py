from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.seed import seed_core_data
from models.platform import Assignment, AuditLog, ClassificationCode, CodingResult, ConsentRecord, IntelligenceSession, Paradata, Response


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
    import services.events as events

    original_store = response_service.store_collection_response

    def store_without_redis(db, payload):
        return original_store(db, payload, event_publisher=lambda events, event_payload: events)

    monkeypatch.setattr(response_service, "store_collection_response", store_without_redis)
    monkeypatch.setattr(events, "publish", lambda event, payload: True)

    client = _client()
    fod = _token(client, "fod", "field123")
    sdrd = _token(client, "sdrd", "design123")
    dpd = _token(client, "dpd", "process123")
    scd = _token(client, "scd", "coord123")

    enumerators = client.get("/api/enumerators", headers=fod)
    assert enumerators.status_code == 200
    assert len(enumerators.json()["enumerators"]) >= 10

    created_survey = client.post(
        "/api/surveys",
        headers=sdrd,
        json={
            "id": "auto-publish-flow",
            "title": {"en": "Auto Publish Flow"},
            "question_graph": {
                "id": "auto-publish-flow",
                "title": {"en": "Auto Publish Flow"},
                "nodes": [{"id": "name", "type": "text", "prepop": True, "q": {"en": "Confirm your name"}}],
                "branches": {},
            },
        },
    )
    assert created_survey.status_code == 200
    published = client.post("/api/surveys/auto-publish-flow/publish", headers=sdrd)
    assert published.status_code == 200
    assert published.json()["assignment"]["enumeratorId"]
    assert published.json()["validationRulesCreated"] >= 1

    auto_assignments = client.get("/api/assignments?survey_id=auto-publish-flow", headers=fod)
    assert auto_assignments.status_code == 200
    auto_assignment = auto_assignments.json()["assignments"][0]
    assert auto_assignment["status"] == "assigned"

    generated_response = client.post(
        "/api/responses",
        headers=fod,
        json={
            "surveyId": "auto-publish-flow",
            "householdId": auto_assignment["householdId"],
            "enumeratorId": auto_assignment["enumeratorId"],
            "assignmentId": auto_assignment["id"],
            "answers": {"name": "Lakshmi R"},
            "speedMode": "normal",
            "elapsedSeconds": 20,
        },
    )
    assert generated_response.status_code == 200
    assert generated_response.json()["responseId"]

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

    assigned = client.get("/api/assignments?survey_id=emp-2026&enumerator_id=ENUM-A&status=assigned", headers=fod)
    assert assigned.status_code == 200
    assignment_id = assigned.json()["assignments"][0]["id"]

    response = client.post(
        "/api/responses",
        headers=fod,
        json={
            "surveyId": "emp-2026",
            "householdId": "HH-TN-0042",
            "enumeratorId": "ENUM-A",
            "assignmentId": assignment_id,
            "answers": {"age": "34", "occupation": "Salaried", "income": "25000", "household": "4"},
            "speedMode": "normal",
            "elapsedSeconds": 90,
        },
    )
    assert response.status_code == 200

    detail = client.get(f"/api/responses/{response.json()['responseId']}", headers=dpd)
    assert detail.status_code == 200
    assert detail.json()["paradata"]["totalSeconds"] >= 1
    assert len(detail.json()["validationFlags"]) >= 5

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

    coding_queue = client.get("/api/coding-review", headers=dpd)
    assert coding_queue.status_code == 200
    assert "items" in coding_queue.json()

    response_review = client.post(
        f"/api/responses/{response.json()['responseId']}/review",
        headers=dpd,
        json={"action": "approve", "reason": "Validation evidence accepted"},
    )
    assert response_review.status_code == 200
    assert response_review.json()["status"] == "approved"

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

    metrics = client.get("/api/dashboard/metrics", headers=scd)
    assert metrics.status_code == 200
    assert metrics.json()["totalResponses"] >= 1

    flags = client.get("/api/dashboard/flags", headers=scd)
    assert flags.status_code == 200
    assert "responses" in flags.json()

    db = SessionLocal()
    try:
        assert db.query(ConsentRecord).count() >= 1
        assert db.query(IntelligenceSession).count() >= 1
        assert db.query(Response).count() >= 1
        assert db.query(Paradata).count() >= 1
        assert db.get(Assignment, assignment_id).status == "submitted"
        assert db.query(CodingResult).count() >= 1
        assert db.query(AuditLog).count() >= 1
    finally:
        db.close()


def test_classification_codes_endpoints_persist():
    client = _client()
    sdrd = _token(client, "sdrd", "design123")

    db = SessionLocal()
    try:
        for idx in range(12):
            db.add(ClassificationCode(
                code=f"ZZ{idx:03d}",
                code_type="NIC",
                label=f"Filler NIC {idx}",
                synonyms=[],
                external_source="test",
            ))
        db.add(ClassificationCode(
            code="99999",
            code_type="NIC",
            label="Special spacecraft manufacturing",
            synonyms=["orbital equipment"],
            external_source="test",
        ))
        db.commit()
    finally:
        db.close()

    # Test GET /api/codes
    res = client.get("/api/codes", headers=sdrd)
    assert res.status_code == 200
    assert "codes" in res.json()

    # Search must happen in SQL before limit, otherwise large parsed NIC/NCO
    # libraries hide valid rows outside the first page.
    searched = client.get("/api/codes?type=NIC&q=spacecraft&limit=1", headers=sdrd)
    assert searched.status_code == 200
    assert searched.json()["codes"][0]["code"] == "99999"

    # Test GET /api/codes/stats
    stats_res = client.get("/api/codes/stats", headers=sdrd)
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert "stats" in data
    assert "sectors" in data
    assert "sections" in data

