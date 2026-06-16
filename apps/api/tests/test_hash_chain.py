"""Phase 6 — tamper-evident hash-chained response storage."""
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from models.platform import Response
from services.hash_chain import GENESIS_HASH, verify_chain
from services.response_service import store_collection_response

_NOOP = lambda events, payload: events  # noqa: E731


def _seed():
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
        # start each test from a clean chain (session DB is shared across tests)
        from models.platform import CodingResult, Paradata, TrustScore, ValidationResult

        for model in (ValidationResult, TrustScore, CodingResult, Paradata, Response):
            db.query(model).delete()
        db.commit()
    finally:
        db.close()


def _submit(db, answers):
    return store_collection_response(
        db,
        {"surveyId": "emp-2026", "answers": answers, "channel": "web", "enumeratorId": "ENUM-A"},
        event_publisher=_NOOP,
    )


def test_two_submissions_chain_and_verify():
    _seed()
    db = next(get_db())
    try:
        r1 = _submit(db, {"occupation": "Salaried", "income": 25000, "age": 34})
        r2 = _submit(db, {"occupation": "Salaried", "income": 30000, "age": 41})

        a = db.get(Response, r1["responseId"])
        b = db.get(Response, r2["responseId"])
        assert a.chain_index == 0 and a.prev_hash == GENESIS_HASH
        assert b.chain_index == 1 and b.prev_hash == a.content_hash
        assert a.content_hash and b.content_hash and a.content_hash != b.content_hash

        result = verify_chain(db)
        assert result == {"valid": True, "length": 2}
    finally:
        db.close()


def test_tampering_makes_verify_invalid_at_that_index():
    _seed()
    db = next(get_db())
    try:
        _submit(db, {"occupation": "Salaried", "income": 25000, "age": 34})
        r2 = _submit(db, {"occupation": "Salaried", "income": 30000, "age": 41})
        assert verify_chain(db)["valid"] is True

        # tamper with the stored answers of the second response, out of band
        victim = db.get(Response, r2["responseId"])
        victim.answers = {**victim.answers, "income": 999999}
        db.commit()

        result = verify_chain(db)
        assert result["valid"] is False
        assert result["broken_index"] == 1
    finally:
        db.close()


def test_sealed_audit_row_written():
    _seed()
    db = next(get_db())
    try:
        from models.platform import AuditLog

        r = _submit(db, {"occupation": "Salaried", "income": 25000, "age": 34})
        sealed = (
            db.query(AuditLog)
            .filter(AuditLog.action == "response.sealed", AuditLog.entity_id == r["responseId"])
            .first()
        )
        assert sealed is not None
        assert sealed.payload["hash"] == db.get(Response, r["responseId"]).content_hash
        assert sealed.reason
    finally:
        db.close()
