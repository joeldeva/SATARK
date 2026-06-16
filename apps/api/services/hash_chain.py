"""Tamper-evident response storage — a hash chain in Postgres (no blockchain).

Each sealed response stores:
    content_hash = sha256(prev_hash + canonical_json(payload))
where ``prev_hash`` is the content_hash of the previous response in a single
global chain (ordered by chain_index; genesis prev_hash = 64 zeros).

GET /api/integrity/verify walks the chain, recomputes every hash and returns
{valid:true, length:N} or the first broken index — so any post-hoc edit to a
stored answer is detectable.

Chain append is serialized with a Postgres advisory lock (xact-scoped) to avoid
a race on chain_index under concurrency; on sqlite this is a no-op.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

GENESIS_HASH = "0" * 64
_ADVISORY_LOCK_KEY = 0x5A_7A_10  # arbitrary, stable per-process key for the chain


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def chain_payload(
    *,
    response_id: str,
    survey_id: str,
    enumerator_id: Optional[str],
    answers: dict[str, Any],
    paradata: dict[str, Any],
    confidence: Optional[float],
    trust_level: Optional[str],
    submitted_at: str,
) -> dict[str, Any]:
    """The canonical, stable basis hashed for one response."""
    return {
        "response_id": str(response_id),
        "survey_id": survey_id,
        "enumerator_id": enumerator_id,
        "answers": answers or {},
        "paradata": paradata or {},
        "confidence": confidence,
        "trust_level": trust_level,
        "submitted_at": submitted_at,
    }


def stable_paradata(paradata_values: dict[str, Any]) -> dict[str, Any]:
    """Subset of paradata that is deterministically reconstructable for verify."""
    return {
        "total_seconds": paradata_values.get("total_seconds"),
        "question_timings": paradata_values.get("question_timings") or {},
        "correction_count": paradata_values.get("correction_count"),
        "back_nav_count": paradata_values.get("back_nav_count"),
        "pauses": paradata_values.get("pauses"),
        "mode": paradata_values.get("mode"),
    }


def compute_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()


def acquire_chain_lock(db) -> None:
    """Serialize chain append on Postgres; no-op elsewhere."""
    try:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})
    except Exception:  # noqa: BLE001 — locking is best-effort, never fatal to a seal
        pass


def previous_link(db):
    """Return (prev_hash, next_index) for the next response in the global chain."""
    from models.platform import Response

    prev = (
        db.query(Response)
        .filter(Response.chain_index.isnot(None))
        .order_by(Response.chain_index.desc())
        .first()
    )
    if prev is None:
        return GENESIS_HASH, 0
    return prev.content_hash, int(prev.chain_index) + 1


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_seconds(dt: datetime | None) -> str:
    """Stable, storage-agnostic UTC timestamp (second precision, 'Z').

    Used identically at seal time and verify time so the hashed ``submitted_at``
    round-trips through both sqlite (naive) and Postgres (tz-aware) unchanged.
    """
    if dt is None:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_chain(db) -> dict[str, Any]:
    """Walk the chain in order, recompute hashes, report validity."""
    from models.platform import Paradata, Response

    rows = (
        db.query(Response)
        .filter(Response.chain_index.isnot(None))
        .order_by(Response.chain_index.asc())
        .all()
    )
    expected_prev = GENESIS_HASH
    for row in rows:
        if (row.prev_hash or GENESIS_HASH) != expected_prev:
            return {"valid": False, "broken_index": int(row.chain_index), "reason": "prev_hash mismatch", "length": len(rows)}
        paradata_row = (
            db.query(Paradata)
            .filter(Paradata.response_id == row.id)
            .order_by(Paradata.created_at.asc())
            .first()
        )
        paradata = stable_paradata(_paradata_to_values(paradata_row)) if paradata_row else {}
        payload = chain_payload(
            response_id=row.id,
            survey_id=row.survey_id,
            enumerator_id=row.enumerator_id,
            answers=row.answers or {},
            paradata=paradata,
            confidence=row.confidence_score,
            trust_level=row.trust_level,
            submitted_at=iso_seconds(row.created_at),
        )
        recomputed = compute_hash(row.prev_hash or GENESIS_HASH, payload)
        if recomputed != row.content_hash:
            return {"valid": False, "broken_index": int(row.chain_index), "reason": "content_hash mismatch", "length": len(rows)}
        expected_prev = row.content_hash
    return {"valid": True, "length": len(rows)}


def _paradata_to_values(row) -> dict[str, Any]:
    return {
        "total_seconds": row.total_seconds,
        "question_timings": row.question_timings or {},
        "correction_count": row.correction_count,
        "back_nav_count": row.back_nav_count,
        "pauses": row.pauses,
        "mode": row.mode,
    }
