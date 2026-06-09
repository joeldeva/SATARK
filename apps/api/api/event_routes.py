from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.rbac import user_from_token
from app.config import settings
from services.events import RedisPublishError


router = APIRouter()


def _redis_client():
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


@router.websocket("/events/live")
async def live_events(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    user = user_from_token(token)
    if not user or "dashboard:view" not in user["scopes"]:
        await websocket.close(code=1008)
        return

    event_filter = websocket.query_params.get("event")
    try:
        client = _redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe("satark:events")
    except RedisPublishError:
        await websocket.close(code=1011)
        return

    await websocket.accept()
    receive_task = asyncio.create_task(websocket.receive_text())
    try:
        await websocket.send_json({"event": "connected", "source": "redis", "is_verdict": False})
        while True:
            if receive_task.done():
                receive_task.result()
                receive_task = asyncio.create_task(websocket.receive_text())
            message = await asyncio.to_thread(
                pubsub.get_message,
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if not message:
                await asyncio.sleep(0.05)
                continue
            payload = _decode_message(message)
            if not payload:
                continue
            if event_filter and payload.get("event") != event_filter:
                continue
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        if not receive_task.done():
            receive_task.cancel()
        await asyncio.to_thread(pubsub.close)


def _decode_message(message: dict[str, Any]) -> dict[str, Any] | None:
    data = message.get("data")
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return data if isinstance(data, dict) else None
