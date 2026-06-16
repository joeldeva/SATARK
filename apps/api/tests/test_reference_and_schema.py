"""Per-stratum reference bands + validation-rule schema enforcement."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from services.response_service import store_collection_response

_NOOP = lambda events, payload: events  # noqa: E731


class FakeGenerator:
    def generate(self, prompt, user_id):
        return {"survey_id": "x", "title": "x", "questions": [], "metadata": {"assist": {"is_verdict": False}}}


def _seed():
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()


def _client():
    _seed()
    set_db_dependency(get_db)
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _headers(client):
    r = client.post("/api/auth/login", json={"username": "sdrd", "password": "design123"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _context_layer(result):
    return next(layer for layer in result["intelligence"]["layers"] if layer["layer"] == "Context")


# ---- per-stratum reference bands ----

def test_resolver_picks_stratum_by_occupation_value():
    _seed()
    from models.platform import ReferenceDistribution
    from services.reference import resolve_reference

    db = next(get_db())
    try:
        rows = db.query(ReferenceDistribution).filter(ReferenceDistribution.key == "income").all()
        unemployed = resolve_reference(rows, {"LAB_001": "Unemployed", "emp_003": 200000})["income"]
        salaried = resolve_reference(rows, {"occupation": "Salaried"})["income"]
        default = resolve_reference(rows, {"occupation": "Astronaut"})["income"]
        assert unemployed["p95"] == 12000 and "Unemployed" in unemployed["stratum"]
        assert salaried["p95"] == 120000 and "Salaried" in salaried["stratum"]
        assert default["p95"] == 80000  # falls back to the all-households band
    finally:
        db.close()


def test_context_reason_is_stratum_specific_end_to_end():
    _seed()
    db = next(get_db())
    try:
        suspicious = store_collection_response(
            db, {"surveyId": "emp-2026", "answers": {"occupation": "Unemployed", "income": 200000}, "channel": "web"},
            event_publisher=_NOOP,
        )
        ctx = _context_layer(suspicious)
        assert ctx["status"] == "warn"
        assert "Unemployed households" in ctx["reason"]
        assert "median 3000" in ctx["reason"]

        genuine = store_collection_response(
            db, {"surveyId": "emp-2026", "answers": {"occupation": "Salaried", "income": 25000}, "channel": "web"},
            event_publisher=_NOOP,
        )
        assert _context_layer(genuine)["status"] == "pass"
    finally:
        db.close()


# ---- rule-schema validation ----

def test_malformed_cross_field_rule_rejected():
    client = _client()
    h = _headers(client)
    bad = client.post("/api/validation-rules", headers=h, json={
        "survey_id": "emp-2026", "field": "income", "rule_type": "cross_field",
        "params": {"if_field": "occupation", "if_op": "eq", "if_value": "Unemployed"},  # missing then_*
    })
    assert bad.status_code == 400
    assert "then_field" in bad.json()["detail"] or "missing params" in bad.json()["detail"].lower()


def test_bad_operator_rejected():
    client = _client()
    h = _headers(client)
    bad = client.post("/api/validation-rules", headers=h, json={
        "survey_id": "emp-2026", "field": "income", "rule_type": "cross_field",
        "params": {"if_field": "occupation", "if_op": "EQUALS", "if_value": "Unemployed",
                   "then_field": "income", "then_op": "lte", "then_value": 50000},
    })
    assert bad.status_code == 400


def test_valid_rule_accepted():
    client = _client()
    h = _headers(client)
    ok = client.post("/api/validation-rules", headers=h, json={
        "survey_id": "emp-2026", "field": "age", "rule_type": "range",
        "params": {"field": "age", "min": 18, "max": 95},
    })
    assert ok.status_code == 200, ok.text
