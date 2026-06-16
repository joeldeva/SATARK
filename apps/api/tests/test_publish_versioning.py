"""Re-publishing an edited, already-published survey is a version bump (not a 409)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data


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
    r = client.post("/api/auth/login", json={"username": "sdrd", "password": "design123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _graph(sid, qtext):
    return {
        "id": sid,
        "title": {"en": "Versioned Survey"},
        "nodes": [{"id": "q1", "type": "text", "q": {"en": qtext}}],
        "branches": {},
    }


def test_publish_then_edit_and_republish_bumps_version_no_409():
    client = _client()
    h = _headers(client)
    sid = "ver-survey-1"

    created = client.post("/api/surveys", headers=h, json={"id": sid, "title": {"en": "Versioned Survey"}, "question_graph": _graph(sid, "first?")})
    assert created.status_code == 200, created.text

    first = client.post(f"/api/surveys/{sid}/publish", headers=h, json={})
    assert first.status_code == 200, first.text
    v1 = first.json()["version"]
    assert first.json()["status"] == "published"

    # edit the published survey and re-publish WITH the new graph -> version bump, no 409
    second = client.post(f"/api/surveys/{sid}/publish", headers=h, json={"question_graph": _graph(sid, "edited question?")})
    assert second.status_code == 200, second.text
    assert second.json()["version"] == v1 + 1

    # the edited graph is now persisted
    got = client.get(f"/api/surveys/{sid}", headers=h)
    nodes = got.json()["survey"]["nodes"]
    assert nodes[0]["q"]["en"] == "edited question?"


def test_direct_patch_on_published_still_blocked():
    """The immutability contract still holds for the raw PATCH path."""
    client = _client()
    h = _headers(client)
    sid = "ver-survey-2"
    client.post("/api/surveys", headers=h, json={"id": sid, "title": {"en": "S"}, "question_graph": _graph(sid, "q?")})
    client.post(f"/api/surveys/{sid}/publish", headers=h, json={})
    blocked = client.patch(f"/api/surveys/{sid}", headers=h, json={"title": {"en": "X"}})
    assert blocked.status_code == 409
