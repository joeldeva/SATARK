"""JWT-backed RBAC dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import Header, HTTPException, status

from app.auth.jwt import decode_token
from app.config import settings


PERMISSIONS_BY_ROLE: dict[str, set[str]] = {
    "admin": {
        "admin",
        "survey:read",
        "survey:write",
        "collect:write",
        "coding:review",
        "validation:review",
        "dashboard:view",
    },
    "sdrd": {"survey:read", "survey:write", "dashboard:view", "collect:write"},
    "fod": {"dashboard:view", "collect:write", "survey:read"},
    "dpd": {"coding:review", "validation:review", "dashboard:view", "survey:read"},
    "scd": {"dashboard:view", "survey:read"},
}


def _scopes_for(role: str, explicit_scopes: Optional[list[str]] = None) -> set[str]:
    if explicit_scopes:
        return set(explicit_scopes)
    return set(PERMISSIONS_BY_ROLE.get(role or "", set()))


def user_from_token(token: str) -> Optional[dict]:
    payload = decode_token(token, settings.SECRET_KEY)
    if not payload:
        return None
    role = str(payload.get("role") or "")
    return {
        "username": payload.get("sub") or "",
        "role": role,
        "name": payload.get("name") or "",
        "scopes": _scopes_for(role, payload.get("scopes")),
        "source": "jwt",
    }


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Return the authenticated user from a valid bearer token."""

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.split(" ", 1)[1].strip()
    user = user_from_token(token)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


def require_scope(*required: str) -> Callable:
    """Return a dependency that ensures the bearer token has all scopes."""

    required_set = set(required)

    def _dependency(authorization: Optional[str] = Header(default=None)) -> dict:
        user = get_current_user(authorization=authorization)
        if not required_set.issubset(user["scopes"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope(s): {sorted(required_set - user['scopes'])}",
            )
        return user

    return _dependency
