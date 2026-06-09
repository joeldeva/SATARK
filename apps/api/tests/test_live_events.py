import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.event_routes import router
from app.auth.jwt import encode_token
from app.config import settings


class FakePubSub:
    def __init__(self):
        self.sent = False

    def subscribe(self, channel: str):
        assert channel == "satark:events"

    def get_message(self, ignore_subscribe_messages: bool, timeout: float):
        assert ignore_subscribe_messages is True
        assert timeout == 1.0
        if self.sent:
            return None
        self.sent = True
        return {
            "type": "message",
            "data": json.dumps({
                "event": "flag.created",
                "response_id": "response-1",
                "risk_level": "Red",
            }),
        }

    def close(self):
        return None


class FakeRedis:
    def __init__(self):
        self.pubsub_instance = FakePubSub()

    def pubsub(self):
        return self.pubsub_instance


def test_live_events_streams_redis_flags(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    monkeypatch.setattr("api.event_routes._redis_client", lambda: FakeRedis())

    token = encode_token({"sub": "scd", "role": "scd", "name": "Coordination Officer"}, settings.SECRET_KEY)
    client = TestClient(app)
    with client.websocket_connect(f"/api/events/live?token={token}&event=flag.created") as ws:
        assert ws.receive_json()["event"] == "connected"
        event = ws.receive_json()
        assert event["event"] == "flag.created"
        assert event["response_id"] == "response-1"
        assert event["risk_level"] == "Red"


def test_dashboard_live_alias_streams_redis_flags(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    monkeypatch.setattr("api.event_routes._redis_client", lambda: FakeRedis())

    token = encode_token({"sub": "scd", "role": "scd", "name": "Coordination Officer"}, settings.SECRET_KEY)
    client = TestClient(app)
    with client.websocket_connect(f"/api/dashboard/live?token={token}&event=flag.created") as ws:
        assert ws.receive_json()["event"] == "connected"
        assert ws.receive_json()["event"] == "flag.created"


def test_live_events_rejects_non_dashboard_token():
    app = FastAPI()
    app.include_router(router, prefix="/api")

    token = encode_token({"sub": "guest", "role": "guest", "name": "Guest"}, settings.SECRET_KEY)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as info:
        with client.websocket_connect(f"/api/events/live?token={token}"):
            pass
    assert info.value.code == 1008
