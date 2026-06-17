"""One pipeline, all channels.

Drives the channel-neutral loop (start -> consent -> Q&A -> complete) over
whatsapp, ivr, avatar and web and asserts the SAME deterministic engine scores
every channel: a genuine respondent lands Green, a fraudulent one (Unemployed +
₹2,00,000, fast) flags Red with reasons and emits flag.created.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_db_dependency, set_generator
from api.channel_routes import router as channel_router, set_db_dependency as set_channel_db
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from models.survey import Survey


class FakeGenerator:
    def generate(self, prompt: str, user_id: str):
        return {"survey_id": "unused", "title": "Unused", "questions": [], "metadata": {"assist": {"is_verdict": False}}}


def _client() -> TestClient:
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()
    set_db_dependency(get_db)
    set_channel_db(get_db)
    set_generator(FakeGenerator())
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(channel_router, prefix="/api/v1")
    return TestClient(app)


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "fod", "password": "field123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


GENUINE = {
    "name": "Lakshmi R",
    "age": "34",
    "occupation": "Salaried",
    "employer": "Govt",
    "income": "25000",
    "household": "4",
    "institution": "Anna University",
    "unemp_dur": "3",
    "land": "2",
}

SUSPICIOUS = {
    "name": "Lakshmi R",
    "age": "34",
    "occupation": "Unemployed",
    "unemp_dur": "3",
    "income": "200000",
    "household": "4",
}


def _answer(client, headers, channel, ref, raw, elapsed):
    return client.post(
        "/api/v1/channels/answer",
        headers=headers,
        json={"channel": channel, "respondent_ref": ref, "raw_answer": raw, "meta": {"elapsed_seconds": elapsed}},
    )


def _run(client, headers, channel, ref, start_payload, answer_map, fast_fields):
    """Drive the loop to completion, returning the final 'complete' payload."""
    last = start_payload
    for _ in range(30):
        if last.get("type") == "complete":
            return last
        node = last.get("node_id")
        raw = answer_map.get(node, "1")
        elapsed = 4 if node in fast_fields else 20
        resp = _answer(client, headers, channel, ref, raw, elapsed)
        assert resp.status_code == 200, resp.text
        last = resp.json()
    return last


@pytest.mark.parametrize("channel", ["whatsapp", "ivr", "avatar", "web"])
def test_channel_loop_genuine_lands_green(channel):
    client = _client()
    headers = _headers(client)
    ref = f"+9199{uuid.uuid4().hex[:8]}"

    started = client.post(
        "/api/v1/channels/session/start",
        headers=headers,
        json={"survey_id": "emp-2026", "channel": channel, "respondent_ref": ref},
    )
    assert started.status_code == 200, started.text
    assert started.json()["type"] == "consent"

    # consent yes -> first question
    consented = _answer(client, headers, channel, ref, "yes", 20)
    assert consented.status_code == 200
    assert consented.json()["type"] == "question"
    assert consented.json()["node_id"] == "name"

    final = _run(client, headers, channel, ref, consented.json(), GENUINE, fast_fields=set())
    assert final is not None and final["type"] == "complete"
    assert final["last_result"]["risk_level"] == "Green"
    assert final["last_result"]["confidence"] >= 90
    # every layer carries a reason
    for layer in final["last_result"]["layers"]:
        assert layer["reason"]


@pytest.mark.parametrize("channel", ["whatsapp", "ivr", "avatar", "web"])
def test_channel_loop_suspicious_flags_red(channel):
    client = _client()
    headers = _headers(client)
    ref = f"+9188{uuid.uuid4().hex[:8]}"

    started = client.post(
        "/api/v1/channels/session/start",
        headers=headers,
        json={"survey_id": "emp-2026", "channel": channel, "respondent_ref": ref},
    )
    assert started.status_code == 200
    consented = _answer(client, headers, channel, ref, "yes", 20)

    final = _run(client, headers, channel, ref, consented.json(), SUSPICIOUS, fast_fields={"income", "household"})
    assert final is not None and final["type"] == "complete"
    assert final["last_result"]["risk_level"] == "Red"
    assert final["last_result"]["confidence"] < 50
    assert "flag.created" in final.get("events", [])
    reasons = " ".join(
        layer["reason"] for layer in final["last_result"]["layers"] if layer["status"] in {"fail", "warn"}
    ).lower()
    assert "contradict" in reasons or "median" in reasons or "pace" in reasons


def test_next_is_idempotent_and_does_not_advance():
    client = _client()
    headers = _headers(client)
    ref = f"+9177{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/channels/session/start",
        headers=headers,
        json={"survey_id": "emp-2026", "channel": "ivr", "respondent_ref": ref},
    )
    _answer(client, headers, "ivr", ref, "yes", 20)
    params = {"channel": "ivr", "respondent_ref": ref}
    a = client.get("/api/v1/channels/next", params=params, headers=headers)
    b = client.get("/api/v1/channels/next", params=params, headers=headers)
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["node_id"] == b.json()["node_id"] == "name"
    # ivr helpers present
    assert "speak_text" in a.json()


def test_whatsapp_and_ivr_webhooks_drive_the_same_loop():
    client = _client()
    headers = _headers(client)

    # WhatsApp (Baileys-style payload) — webhook is open (external bridge)
    wa_ref = f"wa-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/channels/session/start",
        headers=headers,
        json={"survey_id": "emp-2026", "channel": "whatsapp", "respondent_ref": wa_ref},
    )
    reply = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": wa_ref, "text": "yes"})
    assert reply.status_code == 200
    assert reply.json()["payload"]["node_id"] == "name"

    # IVR (DTMF) — start then drive via webhook
    ivr_ref = f"CALL-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/channels/session/start",
        headers=headers,
        json={"survey_id": "emp-2026", "channel": "ivr", "respondent_ref": ivr_ref},
    )
    ivr = client.post("/api/v1/channels/ivr/webhook", json={"CallSid": ivr_ref, "Digits": "1"})
    assert ivr.status_code == 200
    assert ivr.json()["payload"]["node_id"] == "name"
    assert ivr.json()["expect"] in {"dtmf", "speech"}


def test_real_whatsapp_first_contact_auto_starts_session():
    """A citizen simply messaging in (no prior session) auto-starts the loop."""
    client = _client()
    ref = f"wa-{uuid.uuid4().hex[:8]}"
    # first inbound message — no session yet -> auto-start returns consent
    first = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "hi"})
    assert first.status_code == 200
    assert first.json()["payload"]["type"] == "consent"
    assert first.json()["reply"]  # bridge-compatible field present
    # consent -> first question
    second = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "yes"})
    assert second.json()["payload"]["type"] == "question"
    assert second.json()["payload"]["node_id"] == "name"


def test_meta_whatsapp_webhook_sends_reply_through_provider(monkeypatch):
    import api.channel_routes as channel_routes

    client = _client()
    sent = {}

    async def fake_send(to, reply):
        sent["to"] = to
        sent["reply"] = reply
        return {"sent": True, "provider": "meta", "status_code": 200}

    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "meta")
    monkeypatch.setattr(channel_routes, "_send_meta_whatsapp", fake_send)

    response = client.post(
        "/api/v1/channels/whatsapp/webhook",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "919900001111",
                                        "text": {"body": "hi"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["provider_delivery"]["sent"] is True
    assert sent["to"] == "919900001111"
    assert "consent" in response.json()["payload"]["type"]
    assert sent["reply"]


def test_whatsapp_default_prefers_full_generated_companion_over_short_shell():
    client = _client()
    base = f"DDI-IND-MOSPI-TEST{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)

    def graph(survey_id, count, prefix):
        return {
            "id": survey_id,
            "title": {"en": survey_id},
            "nodes": [
                {"id": f"{prefix}_{idx}", "type": "text", "q": {"en": f"{prefix} question {idx}"}}
                for idx in range(1, count + 1)
            ],
            "branches": {},
        }

    db = next(get_db())
    try:
        draft_id = f"{base}-DRAFT-0001"
        draft_graph = graph(draft_id, 8, "draft")
        shell_graph = graph(base, 5, "shell")
        db.add(
            Survey(
                survey_id=draft_id,
                title="Generated full survey",
                domain="test",
                status="published",
                survey_data=draft_graph,
                question_graph=draft_graph,
                total_questions=8,
                created_at=now - timedelta(minutes=1),
                published_at=now - timedelta(minutes=1),
            )
        )
        db.add(
            Survey(
                survey_id=base,
                title="Published DDI shell",
                domain="test",
                status="published",
                survey_data=shell_graph,
                question_graph=shell_graph,
                total_questions=5,
                created_at=now,
                published_at=now,
            )
        )
        db.commit()
    finally:
        db.close()

    ref = f"wa-{uuid.uuid4().hex[:8]}"
    first = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "hi"})
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "yes"})
    assert second.status_code == 200, second.text
    assert second.json()["payload"]["node_id"] == "draft_1"


def test_whatsapp_default_skips_latest_too_short_published_shell():
    client = _client()
    db = next(get_db())
    try:
        full_id = f"DDI-IND-MOSPI-FULL-{uuid.uuid4().hex[:6].upper()}"
        shell_id = f"DDI-IND-MOSPI-SHELL-{uuid.uuid4().hex[:6].upper()}"
        older = datetime.now(timezone.utc) + timedelta(hours=1)
        newer = older + timedelta(minutes=1)

        full_graph = {
            "id": full_id,
            "title": {"en": "Full Generated Survey"},
            "nodes": [
                {"id": f"full_{idx}", "type": "text", "q": {"en": f"Generated question {idx}"}}
                for idx in range(1, 8)
            ],
            "branches": {},
        }
        shell_graph = {
            "id": shell_id,
            "title": {"en": "Too Short Shell"},
            "nodes": [{"id": "shell_only", "type": "text", "q": {"en": "Placeholder name?"}}],
            "branches": {},
        }
        db.add(
            Survey(
                survey_id=full_id,
                title="Full Generated Survey",
                domain="test",
                status="published",
                survey_data=full_graph,
                question_graph=full_graph,
                total_questions=7,
                created_at=older,
                published_at=older,
            )
        )
        db.add(
            Survey(
                survey_id=shell_id,
                title="Too Short Shell",
                domain="test",
                status="published",
                survey_data=shell_graph,
                question_graph=shell_graph,
                total_questions=1,
                created_at=newer,
                published_at=newer,
            )
        )
        db.commit()
    finally:
        db.close()

    ref = f"wa-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "hi"})
    second = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "yes"})

    assert second.status_code == 200, second.text
    assert second.json()["payload"]["survey_id"] == full_id
    assert second.json()["payload"]["node_id"] == "full_1"


def test_whatsapp_clarification_correction_completes_and_persists():
    client = _client()
    ref = f"wa-{uuid.uuid4().hex[:8]}"
    steps = ["hi", "yes", "Test User", "34", "Salaried", "Govt", "25000", "25000"]
    last = None
    for text in steps:
        response = client.post(
            "/api/v1/channels/whatsapp/webhook",
            json={"sender": ref, "text": text, "survey_id": "emp-2026"},
        )
        assert response.status_code == 200, response.text
        last = response.json()["payload"]

    assert last["type"] == "clarification"
    assert last["node_id"] == "household"

    corrected = client.post(
        "/api/v1/channels/whatsapp/webhook",
        json={"sender": ref, "text": "4", "survey_id": "emp-2026"},
    )
    assert corrected.status_code == 200, corrected.text
    payload = corrected.json()["payload"]
    assert payload["type"] == "complete"
    assert payload["result"]["responseId"]


def test_whatsapp_restart_resets_active_session_to_latest_survey_start():
    client = _client()
    ref = f"wa-{uuid.uuid4().hex[:8]}"

    client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "hi", "survey_id": "emp-2026"})
    first_question = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "yes"})
    assert first_question.json()["payload"]["node_id"] == "name"

    restarted = client.post("/api/v1/channels/whatsapp/webhook", json={"sender": ref, "text": "restart"})
    assert restarted.status_code == 200, restarted.text
    payload = restarted.json()["payload"]
    assert payload["type"] == "consent"
    assert payload["node_id"] == "__consent__"
