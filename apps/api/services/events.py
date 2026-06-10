from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


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
    _emit_superplane_compatible_event(event, body)
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
        _emit_superplane_compatible_event(event, event_payload)
        published.append(event)
    return published


def _emit_superplane_compatible_event(event: str, payload: dict[str, Any]) -> None:
    """Optional non-blocking workflow hook.

    SATARK verdict persistence must never depend on a workflow control plane.
    When configured, this sends an event-shaped payload that SuperPlane can use
    as a trigger for canvases such as DPD review, re-interview, or trust alerts.
    """

    if not settings.SUPERPLANE_WEBHOOK_URL:
        return
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        if settings.SUPERPLANE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.SUPERPLANE_TOKEN}"
        httpx.post(
            settings.SUPERPLANE_WEBHOOK_URL,
            headers=headers,
            json={
                "source": "satark",
                "event": event,
                "payload": payload,
                "workflow_hint": {
                    "canvas": "satark-collection-operations",
                    "trigger": event,
                    "verdict_lane": event in {"response.scored", "flag.created", "trust.updated"},
                },
            },
            timeout=2,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SuperPlane-compatible workflow event failed for %s: %s", event, exc)
