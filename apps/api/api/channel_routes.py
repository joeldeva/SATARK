"""Channel API + Enumerator Sandbox routes.

Mounted at /api/v1 → endpoints live under /api/v1/channels/* and /api/v1/sandbox/*.

The channel adapters are thin: they normalise a provider payload into the
channel-neutral {channel, respondent_ref, raw_answer, meta} shape and call the
shared ``channels_service.answer`` — the same scoring loop for every channel.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app import channel_sessions, sandbox_feed
from app.auth.rbac import require_scope, user_from_token
from app.config import settings
from services import channels_service
from services.events import RedisPublishError

router = APIRouter()
logger = logging.getLogger(__name__)

_get_db = None


def set_db_dependency(get_db_func):
    global _get_db
    _get_db = get_db_func


def _open_db():
    if not _get_db:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Database not configured")
    return next(_get_db())


# ---------------------------------------------------------------------------
# Session-driven channel API
# ---------------------------------------------------------------------------

@router.post("/channels/session/start", dependencies=[Depends(require_scope("collect:write"))])
async def channel_session_start(request: Dict[str, Any]):
    db = _open_db()
    try:
        return channels_service.start_session(db, request)
    finally:
        db.close()


@router.post("/channels/answer", dependencies=[Depends(require_scope("collect:write"))])
async def channel_answer(request: Dict[str, Any]):
    db = _open_db()
    try:
        return channels_service.answer(db, request)
    finally:
        db.close()


@router.get("/channels/next", dependencies=[Depends(require_scope("collect:write"))])
async def channel_next(channel: str = Query(...), respondent_ref: str = Query(...)):
    db = _open_db()
    try:
        return channels_service.current_payload(db, channel, respondent_ref)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# WhatsApp bridge (Baileys / Meta)
# ---------------------------------------------------------------------------

@router.get("/channels/whatsapp/webhook")
async def whatsapp_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    # Meta verification handshake.
    if mode == "subscribe" and challenge:
        if settings.WHATSAPP_VERIFY_TOKEN and token != settings.WHATSAPP_VERIFY_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid WhatsApp verify token")
        return int(challenge) if challenge.isdigit() else challenge
    return {"ok": True}


@router.post("/channels/whatsapp/webhook")
async def whatsapp_webhook(request: Dict[str, Any]):
    is_meta = _is_meta_payload(request)
    respondent_ref, text = _normalize_whatsapp(request)
    survey_id = request.get("survey_id") or request.get("surveyId")
    reset = bool(request.get("reset")) or str(text or "").strip().lower() in {"restart", "reset", "start over", "/restart"}
    db = _open_db()
    try:
        if reset:
            channel_sessions.delete("whatsapp", respondent_ref)
            text = "hi"
        outbound = channels_service.inbound(db, "whatsapp", respondent_ref, text, survey_id=survey_id)
    finally:
        db.close()
    reply = (outbound.get("prompt_text") or {}).get("en", "")
    provider_delivery = None
    if is_meta and (settings.WHATSAPP_PROVIDER or "").strip().lower() == "meta":
        provider_delivery = await _send_meta_whatsapp(respondent_ref, reply)
    # `reply` and `reply_text` both returned for bridge compatibility (Baileys/Meta).
    return {
        "reply": reply,
        "reply_text": reply,
        "to": respondent_ref,
        "payload": outbound,
        "provider_delivery": provider_delivery,
    }


# ---------------------------------------------------------------------------
# IVR bridge (telephony provider, DTMF-first; telephony itself stubbed)
# ---------------------------------------------------------------------------

@router.post("/channels/ivr/webhook")
async def ivr_webhook(request: Dict[str, Any]):
    respondent_ref = str(
        request.get("CallSid") or request.get("call_sid") or request.get("From") or request.get("respondent_ref") or ""
    )
    raw = request.get("Digits") or request.get("SpeechResult") or request.get("raw_answer") or ""
    db = _open_db()
    try:
        outbound = channels_service.inbound(db, "ivr", respondent_ref, raw, meta={"dtmf": request.get("Digits")})
    finally:
        db.close()
    return {
        "speak_text": outbound.get("speak_text") or (outbound.get("prompt_text") or {}).get("en", ""),
        "expect": outbound.get("expect", "speech"),
        "options": outbound.get("options"),
        "payload": outbound,
    }


# ---------------------------------------------------------------------------
# AI avatar client (STT transcript in, TTS text out)
# ---------------------------------------------------------------------------

@router.post("/channels/avatar/answer", dependencies=[Depends(require_scope("collect:write"))])
async def avatar_answer(request: Dict[str, Any]):
    db = _open_db()
    try:
        outbound = channels_service.inbound(
            db,
            "avatar",
            request.get("respondent_ref") or request.get("respondentRef"),
            request.get("transcript") or request.get("raw_answer"),
            meta=request.get("meta") or {},
        )
    finally:
        db.close()
    return outbound


# ---------------------------------------------------------------------------
# Enumerator Sandbox feed
# ---------------------------------------------------------------------------

@router.get("/sandbox/turns", dependencies=[Depends(require_scope("dashboard:view"))])
async def sandbox_turns(session_id: str | None = Query(default=None), after: int = Query(default=0)):
    return {"turns": sandbox_feed.turns(session_id=session_id, after=after), "is_verdict": False}


@router.get("/sandbox/sessions", dependencies=[Depends(require_scope("dashboard:view"))])
async def sandbox_sessions():
    return {"sessions": sandbox_feed.active_sessions(), "backend": _session_backend()}


@router.websocket("/sandbox/live")
async def sandbox_live(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    user = user_from_token(token)
    if not user or "dashboard:view" not in user["scopes"]:
        await websocket.close(code=1008)
        return
    try:
        client = _redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe("satark:events")
    except RedisPublishError:
        # No Redis — the sandbox falls back to GET /sandbox/turns polling.
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
            message = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.05)
                continue
            payload = _decode(message)
            if not payload:
                continue
            if payload.get("event") in {"sandbox.turn", "response.scored", "flag.created", "trust.updated"}:
                await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        if not receive_task.done():
            receive_task.cancel()
        await asyncio.to_thread(pubsub.close)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _is_meta_payload(request: Dict[str, Any]) -> bool:
    return isinstance(request.get("entry"), list)


def _normalize_whatsapp(request: Dict[str, Any]) -> tuple[str, str]:
    # Baileys-style: {sender, message:{text}} ; Meta-style entry/changes nesting.
    if request.get("sender") or request.get("from"):
        ref = str(request.get("sender") or request.get("from"))
        text = request.get("text") or (request.get("message") or {}).get("text") or ""
        return ref, str(text)
    try:
        entry = (request.get("entry") or [{}])[0]
        change = (entry.get("changes") or [{}])[0]
        value = change.get("value") or {}
        msg = (value.get("messages") or [{}])[0]
        ref = msg.get("from") or "unknown"
        text = (msg.get("text") or {}).get("body") or msg.get("button", {}).get("text") or ""
        return str(ref), str(text)
    except Exception:  # noqa: BLE001
        return str(request.get("respondent_ref") or "unknown"), str(request.get("raw_answer") or "")


async def _send_meta_whatsapp(to: str, reply: str) -> dict[str, Any]:
    if not reply.strip() or not to or to == "unknown":
        return {"sent": False, "reason": "No recipient or reply text"}
    missing = [
        name
        for name, value in {
            "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
            "WHATSAPP_PHONE_NUMBER_ID": settings.WHATSAPP_PHONE_NUMBER_ID,
        }.items()
        if not value
    ]
    if missing:
        return {"sent": False, "reason": f"Missing {', '.join(missing)}"}

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": reply},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
        return {"sent": True, "provider": "meta", "status_code": response.status_code}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Meta WhatsApp delivery failed: %s", exc)
        return {"sent": False, "provider": "meta", "error": str(exc)}


def _session_backend() -> str:
    from app import channel_sessions

    return channel_sessions.backend()


def _redis_client():
    try:
        import redis  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        raise RedisPublishError(f"Redis package is unavailable: {exc}") from exc
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        raise RedisPublishError(f"Redis is unreachable at {settings.REDIS_URL}: {exc}") from exc


def _decode(message: dict[str, Any]) -> dict[str, Any] | None:
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
