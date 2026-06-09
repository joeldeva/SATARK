"""Minimal HS256 JWT encode/decode using stdlib only."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def encode_token(payload: Dict[str, Any], secret: str, ttl_seconds: int = 60 * 60 * 12) -> str:
    """Encode a JWT with HS256. Adds iat and exp if not present."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    body = dict(payload)
    body.setdefault("iat", now)
    body.setdefault("exp", now + ttl_seconds)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    body_b64 = _b64url_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{body_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{body_b64}.{sig_b64}"


def decode_token(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """Return payload dict if signature and exp are valid, else None."""
    try:
        header_b64, body_b64, sig_b64 = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_b64}.{body_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(body_b64).decode("utf-8"))
    except Exception:
        return None

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        return None
    return payload
