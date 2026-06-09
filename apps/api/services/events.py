from __future__ import annotations

import json
from typing import Any

from app.config import settings


class RedisPublishError(RuntimeError):
    """Raised when a required Redis event cannot be published."""


def _client():
    try:
        import redis
    except Exception as exc:  # noqa: BLE001
        raise RedisPublishError(f"Redis package is unavailable: {exc}") from exc
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        raise RedisPublishError(f"Redis is unreachable at {settings.REDIS_URL}: {exc}") from exc


def publish(event: str, payload: dict[str, Any]) -> bool:
    """Publish one required event to Redis stream and pub/sub."""

    if not event:
        raise RedisPublishError("event name is required")
    client = _client()
    body = {**(payload or {}), "event": event}
    encoded = json.dumps(body, default=str)
    client.xadd("satark:events", {"event": event, "payload": encoded}, maxlen=1000, approximate=True)
    client.publish("satark:events", encoded)
    return True


def publish_intelligence_events(events: list[str], payload: dict[str, Any]) -> list[str]:
    """Publish verdict events after response persistence."""

    if not events:
        return []
    client = _client()
    published: list[str] = []
    for event in events:
        event_payload = {**payload, "event": event}
        encoded = json.dumps(event_payload, default=str)
        client.xadd("satark:events", {"event": event, "payload": encoded}, maxlen=1000, approximate=True)
        client.publish("satark:events", encoded)
        published.append(event)
    return published
