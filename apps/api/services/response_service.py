from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from services import hash_chain

from models.platform import (
    Assignment,
    AuditLog,
    ClassificationCode,
    CodingResult,
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

    session_intelligence = payload.get("intelligence") if payload.get("verdictSource") == "session" else None
    if (
        isinstance(session_intelligence, dict)
        and session_intelligence.get("is_verdict") is True
        and isinstance(session_intelligence.get("native_trust"), dict)
    ):
        intelligence = session_intelligence
    else:
        enumerator_ctx = _enumerator_context(db, enumerator_id)
        intelligence = evaluate_intelligence_contract(
            answers=answers,
            active_question_id=None,
            speed_mode=speed_mode,
            elapsed_seconds=elapsed_seconds,
            rules=_rules_for_survey(db, survey_id),
            reference=_reference(db, answers),
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

    # ── Tamper-evident hash chain (sealed in this same transaction) ──────────
    response.id = uuid.uuid4()
    response.created_at = datetime.now(timezone.utc)
    paradata_values = _paradata_values(answers, speed_mode, elapsed_seconds, payload)
    hash_chain.acquire_chain_lock(db)
    prev_hash, chain_index = hash_chain.previous_link(db)
    chain_basis = hash_chain.chain_payload(
        response_id=str(response.id),
        survey_id=response.survey_id,
        enumerator_id=response.enumerator_id,
        answers=response.answers,
        paradata=hash_chain.stable_paradata(paradata_values),
        confidence=response.confidence_score,
        trust_level=response.trust_level,
        submitted_at=hash_chain.iso_seconds(response.created_at),
    )
    response.prev_hash = prev_hash
    response.chain_index = chain_index
    response.content_hash = hash_chain.compute_hash(prev_hash, chain_basis)

    db.add(response)
    db.flush()

    paradata = Paradata(response_id=response.id, **paradata_values)
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
        status_value = layer["status"]
        db.add(
            ValidationResult(
                response_id=response.id,
                layer=layer["layer"],
                field=None,
                status=status_value,
                severity="error" if status_value == "fail" else "warning" if status_value == "warn" else "info",
                reason=layer["reason"],
                recommended_action=native_trust["recommendation"],
                confidence=layer.get("confidence"),
            )
        )

    for coding_row in _coding_results_for_answers(db, survey, response.id, answers):
        db.add(coding_row)

    _apply_enumerator_update(db, enumerator_id, intelligence.get("enumerator_update"))
    assignment_id = payload.get("assignmentId") or payload.get("assignment_id")
    if assignment_id:
        assignment = db.get(Assignment, assignment_id)
        if assignment:
            previous_status = assignment.status
            assignment.status = "submitted"
            if previous_status != "submitted" and assignment.enumerator_id:
                enumerator = db.get(EnumeratorProfile, assignment.enumerator_id)
                if enumerator:
                    enumerator.completed = int(enumerator.completed or 0) + 1
    db.add(
        AuditLog(
            actor=enumerator_id or "collection-client",
            action="response.submitted",
            entity_type="response",
            entity_id=str(response.id),
            payload={"surveyId": survey_id, "assignmentId": assignment_id, "status": status},
            reason=f"Response submitted with {trust_level} trust level and confidence {intelligence['confidence']}",
        )
    )
    db.add(
        AuditLog(
            actor=enumerator_id or "collection-client",
            action="response.sealed",
            entity_type="response",
            entity_id=str(response.id),
            payload={"hash": response.content_hash, "prev_hash": response.prev_hash, "chain_index": response.chain_index},
            reason=f"Response sealed into tamper-evident chain at index {response.chain_index} with hash {response.content_hash[:12]}…",
        )
    )
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
    paradata = (
        db.query(Paradata)
        .filter(Paradata.response_id == row.id)
        .order_by(Paradata.created_at.desc())
        .first()
    )
    return {
        "id": str(row.id),
        "surveyId": row.survey_id,
        "respondentId": row.household_id,
        "enumeratorId": row.enumerator_id,
        "answers": row.answers,
        "prepopulated": row.prepopulated,
        "qualityScore": row.confidence_score,
        "trustLevel": row.trust_level,
        "status": row.status,
        "integrity": {
            "sealed": bool(row.content_hash),
            "hash": row.content_hash,
            "hashShort": (row.content_hash or "")[:12],
            "chainIndex": row.chain_index,
            "prevHash": row.prev_hash,
        },
        "validationFlags": [
            {"layer": item.layer, "status": item.status, "reason": item.reason, "confidence": item.confidence}
            for item in validations
        ],
        "paradata": None
        if not paradata
        else {
            "totalSeconds": paradata.total_seconds,
            "questionTimings": paradata.question_timings,
            "pauses": paradata.pauses,
            "correctionCount": paradata.correction_count,
            "backNavCount": paradata.back_nav_count,
            "gpsLatitude": paradata.gps_lat,
            "gpsLongitude": paradata.gps_lng,
            "device": paradata.device,
            "mode": paradata.mode,
            "network": paradata.network,
        },
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


def _reference(db, answers: dict[str, Any] | None = None) -> dict[str, Any]:
    from services.reference import resolve_reference

    rows = db.query(ReferenceDistribution).all()
    if not rows:
        raise HTTPException(status_code=409, detail="No reference distributions configured")
    return resolve_reference(rows, answers)


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


def _paradata_values(answers: dict[str, Any], speed_mode: str, elapsed_seconds: float, payload: dict[str, Any]) -> dict[str, Any]:
    seconds = max(1, int(round(elapsed_seconds)))
    return {
        "total_seconds": int(payload.get("durationSeconds") or seconds * max(len(answers), 1)),
        "question_timings": {key: seconds for key in answers},
        "pauses": int(payload.get("pauses") or 0),
        "correction_count": int(payload.get("correctionCount") or (0 if speed_mode == "too-fast" else 1)),
        "back_nav_count": int(payload.get("backNavCount") or 0),
        "gps_lat": payload.get("gpsLatitude"),
        "gps_lng": payload.get("gpsLongitude"),
        "device": payload.get("device"),
        "mode": payload.get("mode") or "web",
        "network": payload.get("network"),
    }


def _response_to_flag(db, row: Response) -> dict[str, Any]:
    enumerator = db.get(EnumeratorProfile, row.enumerator_id) if row.enumerator_id else None
    survey = db.query(Survey).filter(Survey.survey_id == row.survey_id).first()
    validation = (
        db.query(ValidationResult)
        .filter(ValidationResult.response_id == row.id, ValidationResult.status.in_(["fail", "warn"]))
        .order_by(ValidationResult.created_at.asc())
        .first()
    )
    
    # Fetch all validations
    validations = (
        db.query(ValidationResult)
        .filter(ValidationResult.response_id == row.id)
        .order_by(ValidationResult.created_at.asc())
        .all()
    )
    
    # Fetch coding results
    coding_results = db.query(CodingResult).filter(CodingResult.response_id == row.id).all()
    coded_answers = {}
    for cr in coding_results:
        code = "None"
        label = "Uncoded freeform text"
        if cr.approved_code:
            code = cr.approved_code
            label = cr.approved_label or ""
        elif cr.suggestions and isinstance(cr.suggestions, list) and len(cr.suggestions) > 0:
            top = cr.suggestions[0]
            if isinstance(top, dict):
                code = top.get("code") or "None"
                label = top.get("label") or ""
        coded_answers[cr.field] = {
            "code": code,
            "label": label,
            "confidence": cr.confidence,
            "reason": f"Classification mapping for {cr.field}",
        }

    # Fetch paradata
    paradata = (
        db.query(Paradata)
        .filter(Paradata.response_id == row.id)
        .order_by(Paradata.created_at.desc())
        .first()
    )

    return {
        "id": str(row.id),
        "surveyId": row.survey_id,
        "survey": survey.title if survey else row.survey_id,
        "enumeratorId": row.enumerator_id or "unassigned",
        "enumeratorName": enumerator.name if enumerator else row.enumerator_id or "Unassigned",
        "householdId": row.household_id or "unassigned",
        "answers": row.answers or {},
        "codedAnswers": coded_answers,
        "validationFlags": [
            {"layer": item.layer, "status": item.status, "reason": item.reason, "confidence": item.confidence}
            for item in validations
        ],
        "reason": validation.reason if validation else "Trust score marked this response for review",
        "trustScore": row.confidence_score or 0,
        "trustLevel": row.trust_level or "Amber",
        "status": row.status,
        "timestamp": row.created_at.isoformat() if row.created_at else "",
        "paradata": None
        if not paradata
        else {
            "totalSeconds": paradata.total_seconds,
            "questionTimings": paradata.question_timings,
            "pauses": paradata.pauses,
            "correctionCount": paradata.correction_count,
            "backNavCount": paradata.back_nav_count,
            "gpsLatitude": paradata.gps_lat,
            "gpsLongitude": paradata.gps_lng,
            "device": paradata.device,
            "mode": paradata.mode,
            "network": paradata.network,
        },
    }


def _coding_results_for_answers(db, survey: Survey, response_id, answers: dict[str, Any]) -> list[CodingResult]:
    codeable = _codeable_fields(survey)
    rows: list[CodingResult] = []
    for field, code_type in codeable.items():
        raw = str(answers.get(field) or "").strip()
        if not raw:
            continue
        suggestions = _code_suggestions(db, raw, code_type)
        top = suggestions[0] if suggestions else None
        rows.append(
            CodingResult(
                response_id=response_id,
                field=field,
                raw_text=raw,
                suggestions=suggestions,
                approved_code=None,
                approved_label=None,
                source=top.get("source", "local_rag") if top else "local_rag",
                confidence=float(top.get("confidence", 0) if top else 0),
                needs_review=True,
            )
        )
    return rows


def _codeable_fields(survey: Survey) -> dict[str, str]:
    graph = survey.question_graph or survey.survey_data or {}
    fields: dict[str, str] = {}
    for node in graph.get("nodes", []) if isinstance(graph, dict) else []:
        field = node.get("id")
        code_type = node.get("codeType") or node.get("code_type") or node.get("standard_code")
        if field and code_type:
            fields[str(field)] = str(code_type)
    for fallback in ("occupation", "industry"):
        fields.setdefault(fallback, "NCO")
    return fields


def _code_suggestions(db, raw: str, code_type: str) -> list[dict[str, Any]]:
    needle = raw.lower()
    rows = db.query(ClassificationCode).filter(ClassificationCode.code_type == code_type).limit(1000).all()
    suggestions: list[dict[str, Any]] = []
    for row in rows:
        haystack = [row.label or "", row.code or "", *(row.synonyms or [])]
        matched = next((item for item in haystack if item and needle in item.lower()), None)
        reverse_match = next((item for item in haystack if item and item.lower() in needle), None)
        if not matched and not reverse_match:
            continue
        suggestions.append(
            {
                "code": row.code,
                "type": row.code_type,
                "label": row.label,
                "confidence": 96 if matched else 88,
                "source": row.external_source or "local_rag",
                "reason": f"Matched '{raw}' to {row.code_type} {row.code} using persisted classification synonyms",
            }
        )
    return sorted(suggestions, key=lambda item: item["confidence"], reverse=True)[:5]
