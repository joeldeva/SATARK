import pytest
from fastapi import HTTPException

from app.auth.jwt import encode_token
from app.auth.rbac import require_scope
from app.config import settings


def _auth(role: str) -> str:
    token = encode_token({"sub": f"{role}-user", "role": role, "name": role.upper()}, settings.SECRET_KEY)
    return f"Bearer {token}"


def test_sdrd_has_survey_write_scope():
    dep = require_scope("survey:write")
    user = dep(authorization=_auth("sdrd"))
    assert "survey:write" in user["scopes"]
    assert user["role"] == "sdrd"


def test_scd_cannot_publish():
    dep = require_scope("survey:write")
    with pytest.raises(HTTPException) as info:
        dep(authorization=_auth("scd"))
    assert info.value.status_code == 403


def test_admin_required_for_ingest():
    dep = require_scope("admin")
    with pytest.raises(HTTPException) as info:
        dep(authorization=_auth("sdrd"))
    assert info.value.status_code == 403

    user = dep(authorization=_auth("admin"))
    assert "admin" in user["scopes"]


def test_missing_token_is_rejected():
    dep = require_scope("survey:read")
    with pytest.raises(HTTPException) as info:
        dep(authorization=None)
    assert info.value.status_code == 401
