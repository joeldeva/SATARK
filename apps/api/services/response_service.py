from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from models.platform import (
    EnumeratorProfile,
    Paradata,
    ReferenceDistribution,
    Response,
    TrustScore,
    ValidationResult,
    ValidationRuleRecord,
)
from models.survey import Survey
from services.events import publish_intelligence_events
from services.intelligence_adapter import evaluate_intelligence_contract


def store_collection_response(
    db,
    payload: dict[str, Any],
    event_publisher=publish_intelligence_events,
) -> dict[str, Any]:
    survey_id = payload.get("surveyId")
    if not survey_id:
        raise HTTPException(status_code=400, detail="surveyId is required")
    survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    answers = payload.get("answers") or {}
    enumerator_id = payload.get("enumeratorId")
    household_id = payload.get("householdId")
    incoming_intelligence = payload.get("intelligence") or {}
    speed_mode = _speed_mode_from_payload(payload, incoming_intelligence)
    elapsed_seconds = _elapsed_seconds_from_payload(payload, incoming_intelligence, speed_mode)

    enumerator_ctx = _enumerator_context(db, enumerator_id)
    intelligence = evaluate_intelligence_contract(
        answers=answers,
        active_question_id=None,
        speed_mode=speed_mode,
        elapsed_seconds=elapsed_seconds,
        rules=_rules_for_survey(db, survey_id),
        reference=_reference(db),
        enumerator=enumerator_ctx,
    )

    trust_level = intelligence["trustLevel"]
    status = "approved" if trust_level == "Green" else "flagged" if trust_level == "Red" else "captured"
    response = Response(
        survey_id=survey_id,
        enumerator_id=enumerator_id,
        household_id=household_id,
        channel=payload.get("channel") or "collection-client",
        answers=answers,
        prepopulated=payload.get("prepopulated") or {},
        adaptive_log=[intelligence.get("adaptive", {})],
        confidence_score=float(intelligence["confidence"]),
        trust_level=trust_level,
        status=status,
    )
    db.add(response)
    db.flush()

    paradata = _paradata_from_result(response.id, answers, speed_mode, elapsed_seconds, payload)
    db.add(paradata)

    native_trust = intelligence["native_trust"]
    db.add(
        TrustScore(
            response_id=response.id,
            confidence=float(native_trust["confidence"]),
            risk_level=native_trust["risk_level"],
            breakdown=native_trust["breakdown"],
            fraud_signals=native_trust.get("fraud_signals", []),
            recommendation=native_trust["recommendation"],
            reasons=native_trust.get("reasons", []),
        )
    )

    for layer in intelligence["layers"]:
        if layer["status"] in {"warn", "fail"}:
            db.add(
                ValidationResult(
                    response_id=response.id,
                    layer=layer["layer"],
                    field=None,
                    status=layer["status"],
                    severity="error" if layer["status"] == "fail" else "warning",
                    reason=layer["reason"],
                    recommended_action=native_trust["recommendation"],
                )
            )

    _apply_enumerator_update(db, enumerator_id, intelligence.get("enumerator_update"))
    db.commit()

    event_payload = {
        "response_id": str(response.id),
        "enumerator_id": enumerator_id,
        "confidence": intelligence["confidence"],
        "risk_level": trust_level,
        "reasons": native_trust.get("reasons", [])[:3],
    }
    published_events = event_publisher(intelligence.get("events", []), event_payload)

    return {
        "queued": False,
        "responseId": str(response.id),
        "qualityScore": intelligence["confidence"],
        "trustLevel": trust_level,
        "status": status,
        "events": intelligence.get("events", []),
        "publishedEvents": published_events,
        "intelligence": intelligence,
    }


def flagged_responses(db, status: str | None = None) -> list[dict[str, Any]]:
    query = db.query(Response).order_by(Response.created_at.desc())
    if status == "flagged":
        query = query.filter((Response.status == "flagged") | (Response.trust_level == "Red"))
    rows = query.limit(100).all()
    return [_response_to_flag(db, row) for row in rows]


def response_detail(db, response_id: str) -> dict[str, Any] | None:
    row = db.get(Response, response_id)
    if not row:
        return None
    trust = (
        db.query(TrustScore)
        .filter(TrustScore.response_id == row.id)
        .order_by(TrustScore.created_at.desc())
        .first()
    )
    validations = (
        db.query(ValidationResult)
        .filter(ValidationResult.response_id == row.id)
        .order_by(ValidationResult.created_at.asc())
        .all()
    )
    return {
        "id": str(row.id),
        "surveyId": row.survey_id,
        "respondentId": row.household_id,
        "answers": row.answers,
        "qualityScore": row.confidence_score,
        "trustLevel": row.trust_level,
        "status": row.status,
        "validationFlags": [
            {"layer": item.layer, "status": item.status, "reason": item.reason}
            for item in validations
        ],
        "trust": None
        if not trust
        else {
            "confidence": trust.confidence,
            "risk_level": trust.risk_level,
            "breakdown": trust.breakdown,
            "fraud_signals": trust.fraud_signals,
            "recommendation": trust.recommendation,
            "reasons": trust.reasons,
        },
    }


def _rules_for_survey(db, survey_id: str) -> list[dict[str, Any]]:
    rows = db.query(ValidationRuleRecord).filter(ValidationRuleRecord.survey_id == survey_id).all()
    if not rows:
        raise HTTPException(status_code=409, detail=f"No validation rules configured for survey '{survey_id}'")
    return [
        {
            "field": row.field,
            "rule_type": row.rule_type,
            "severity": row.severity,
            "params": row.params,
            "reason_template": row.reason_template,
        }
        for row in rows
    ]


def _reference(db) -> dict[str, Any]:
    rows = db.query(ReferenceDistribution).all()
    if not rows:
        raise HTTPException(status_code=409, detail="No reference distributions configured")
    return {
        row.key: {
            "stratum": row.stratum,
            "p05": row.p05,
            "median": row.median,
            "p95": row.p95,
            "params": row.params or {},
        }
        for row in rows
    }


def _enumerator_context(db, enumerator_id: str | None) -> dict[str, Any] | None:
    if not enumerator_id:
        return None
    enumerator = db.get(EnumeratorProfile, enumerator_id)
    if not enumerator:
        return None
    return {
        "score": enumerator.trust_score,
        "trend": enumerator.trust_trend or [],
        "level": enumerator.trust_level,
    }


def _apply_enumerator_update(db, enumerator_id: str | None, update: dict[str, Any] | None) -> None:
    if not enumerator_id or not update:
        return
    enumerator = db.get(EnumeratorProfile, enumerator_id)
    if not enumerator:
        return
    enumerator.trust_score = update["score"]
    enumerator.trust_level = update["level"]
    enumerator.trust_trend = update["trend"]


def _speed_mode_from_payload(payload: dict[str, Any], intelligence: dict[str, Any]) -> str:
    if payload.get("speedMode"):
        return payload["speedMode"]
    layers = intelligence.get("layers") or []
    if any(layer.get("layer") == "Behaviour" and layer.get("status") == "fail" for layer in layers):
        return "too-fast"
    if intelligence.get("trustLevel") == "Red" and intelligence.get("confidence", 100) < 55:
        return "too-fast"
    return "normal"


def _elapsed_seconds_from_payload(payload: dict[str, Any], intelligence: dict[str, Any], speed_mode: str) -> float:
    if payload.get("elapsedSeconds"):
        return float(payload["elapsedSeconds"])
    if payload.get("durationSeconds"):
        answers = payload.get("answers") or {}
        return max(1, float(payload["durationSeconds"]) / max(len(answers), 1))
    if speed_mode == "too-fast":
        return 4
    if intelligence.get("scores", {}).get("engagement", 100) < 60:
        return 10
    return 90


def _paradata_from_result(response_id, answers: dict[str, Any], speed_mode: str, elapsed_seconds: float, payload: dict[str, Any]) -> Paradata:
    seconds = max(1, int(round(elapsed_seconds)))
    return Paradata(
        response_id=response_id,
        total_seconds=int(payload.get("durationSeconds") or seconds * max(len(answers), 1)),
        question_timings={key: seconds for key in answers},
        pauses=int(payload.get("pauses") or 0),
        correction_count=int(payload.get("correctionCount") or (0 if speed_mode == "too-fast" else 1)),
        back_nav_count=int(payload.get("backNavCount") or 0),
        gps_lat=payload.get("gpsLatitude"),
        gps_lng=payload.get("gpsLongitude"),
        device=payload.get("device"),
        mode=payload.get("mode") or "web",
        network=payload.get("network"),
    )


def _response_to_flag(db, row: Response) -> dict[str, Any]:
    enumerator = db.get(EnumeratorProfile, row.enumerator_id) if row.enumerator_id else None
    survey = db.query(Survey).filter(Survey.survey_id == row.survey_id).first()
    validation = (
        db.query(ValidationResult)
        .filter(ValidationResult.response_id == row.id)
        .order_by(ValidationResult.created_at.asc())
        .first()
    )
    return {
        "id": str(row.id),
        "enumeratorId": row.enumerator_id or "unassigned",
        "enumeratorName": enumerator.name if enumerator else row.enumerator_id or "Unassigned",
        "survey": survey.title if survey else row.survey_id,
        "reason": validation.reason if validation else "Trust score marked this response for review",
        "trustScore": row.confidence_score or 0,
        "trustLevel": row.trust_level or "Amber",
        "timestamp": row.created_at.isoformat() if row.created_at else "",
    }
