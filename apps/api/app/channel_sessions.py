"""Channel session store for the multi-channel collection loop.

A survey over a stateless channel (IVR / WhatsApp / avatar) is a server-driven
state machine: the server always owns "what question is next"; the channel only
relays text / DTMF / voice.  This module stores that per-respondent session.

Primary backend is Redis (key ``channel:session:{channel}:{respondent_ref}``,
TTL 1h) exactly as specified.  When Redis is unavailable (tests, offline demo
box) it transparently falls back to an in-process dict so the contract and the
API stay fully testable without external infrastructure.

This store is a thin I/O helper.  It NEVER scores anything — scoring lives in
the single deterministic entry point (``evaluate_intelligence_contract``).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 3600
_KEY_PREFIX = "channel:session"

# Process-local fallback store: {key: (expires_at, json_state)}
_MEMORY: dict[str, tuple[float, str]] = {}

# Cached Redis client + availability probe. Reconnecting on every save/load is
# both slow (a refused connection per turn) and pointless — cache the result and
# re-probe only every _PROBE_TTL seconds.
_CLIENT = None
_CLIENT_CHECKED_AT = 0.0
_PROBE_TTL = 30.0


def _key(channel: str, respondent_ref: str) -> str:
    return f"{_KEY_PREFIX}:{(channel or '').strip().lower()}:{(respondent_ref or '').strip()}"


def _redis():
    """Return a live Redis client or None (never raises), cached per process."""
    global _CLIENT, _CLIENT_CHECKED_AT
    now = time.time()
    if _CLIENT is not None and (now - _CLIENT_CHECKED_AT) < _PROBE_TTL:
        return _CLIENT
    if _CLIENT is None and (now - _CLIENT_CHECKED_AT) < _PROBE_TTL:
        return None  # negative cache — do not retry a refused connection every turn
    try:
        import redis  # noqa: PLC0415

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=0.5)
        client.ping()
        _CLIENT = client
    except Exception as exc:  # noqa: BLE001
        logger.debug("Channel session store falling back to memory: %s", exc)
        _CLIENT = None
    _CLIENT_CHECKED_AT = now
    return _CLIENT


def save(channel: str, respondent_ref: str, state: dict[str, Any]) -> None:
    key = _key(channel, respondent_ref)
    encoded = json.dumps(state, default=str)
    client = _redis()
    if client is not None:
        try:
            client.set(key, encoded, ex=SESSION_TTL_SECONDS)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis set failed for %s, using memory: %s", key, exc)
    _MEMORY[key] = (time.time() + SESSION_TTL_SECONDS, encoded)


def load(channel: str, respondent_ref: str) -> Optional[dict[str, Any]]:
    key = _key(channel, respondent_ref)
    client = _redis()
    if client is not None:
        try:
            raw = client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis get failed for %s, using memory: %s", key, exc)
    entry = _MEMORY.get(key)
    if not entry:
        return None
    expires_at, encoded = entry
    if expires_at < time.time():
        _MEMORY.pop(key, None)
        return None
    return json.loads(encoded)


def delete(channel: str, respondent_ref: str) -> None:
    key = _key(channel, respondent_ref)
    client = _redis()
    if client is not None:
        try:
            client.delete(key)
        except Exception:  # noqa: BLE001
            pass
    _MEMORY.pop(key, None)


def backend() -> str:
    return "redis" if _redis() is not None else "memory"
