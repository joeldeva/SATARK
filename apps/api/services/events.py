from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def publish_intelligence_events(events: list[str], payload: dict[str, Any]) -> list[str]:
    """Publish to Redis after persistence. Redis outages do not undo stored responses."""

    if not events:
        return []
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        published: list[str] = []
        encoded_payload = json.dumps(payload, default=str)
        for event in events:
            event_payload = {**payload, "event": event}
            client.xadd("satark:events", {"event": event, "payload": json.dumps(event_payload, default=str)}, maxlen=1000, approximate=True)
            client.publish("satark:events", encoded_payload)
            published.append(event)
        return published
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis event publish failed after persistence: %s", exc)
        return []
