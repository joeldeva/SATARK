"""Enumerator Sandbox live feed.

Every channel answer publishes a ``sandbox.turn`` event so the dashboard
Enumerator Sandbox can render the send -> answer -> validate -> next loop in
real time across channels.  Events go to Redis pub/sub (reusing the dashboard
stream) when available, and are always mirrored into a small in-process ring
buffer so the 3s GET polling fallback works without Redis.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Deque

logger = logging.getLogger(__name__)

_MAX_TURNS = 200
_BUFFER: Deque[dict[str, Any]] = deque(maxlen=_MAX_TURNS)
_SEQ = 0


def record_turn(turn: dict[str, Any]) -> dict[str, Any]:
    """Append a sandbox turn to the buffer and best-effort publish to Redis."""
    global _SEQ
    _SEQ += 1
    enriched = {**turn, "seq": _SEQ, "event": "sandbox.turn"}
    _BUFFER.append(enriched)
    _publish(enriched)
    return enriched


def turns(session_id: str | None = None, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
    items = [t for t in _BUFFER if t.get("seq", 0) > after]
    if session_id:
        items = [t for t in items if t.get("session_id") == session_id]
    return items[-limit:]


def active_sessions() -> list[dict[str, Any]]:
    """Most recent turn per active session, for the 'Active sessions' strip."""
    by_session: dict[str, dict[str, Any]] = {}
    for turn in _BUFFER:
        sid = turn.get("session_id")
        if sid:
            by_session[sid] = turn
    out = []
    for sid, turn in by_session.items():
        out.append(
            {
                "session_id": sid,
                "channel": turn.get("channel"),
                "node_id": turn.get("node_id"),
                "last_seq": turn.get("seq"),
                "risk_level": (turn.get("result") or {}).get("risk_level"),
            }
        )
    return sorted(out, key=lambda item: item.get("last_seq") or 0, reverse=True)


def _publish(turn: dict[str, Any]) -> None:
    # Skip the publish path entirely when Redis is unavailable (cached probe) so
    # we never pay a refused-connection per turn — the GET buffer is the fallback.
    from app import channel_sessions  # noqa: PLC0415

    if channel_sessions.backend() != "redis":
        return
    try:
        from services.events import publish  # noqa: PLC0415

        publish("sandbox.turn", turn)
    except Exception as exc:  # noqa: BLE001 — Redis optional; buffer is the fallback
        logger.debug("sandbox.turn publish skipped (no Redis): %s", exc)
