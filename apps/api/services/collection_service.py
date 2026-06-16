from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from models.platform import (
    Assignment,
    EnumeratorProfile,
    Household,
    IntelligenceSession,
    ReferenceDistribution,
    ValidationRuleRecord,
)
from models.survey import AdaptiveLogicRecord, Survey
from services.intelligence_adapter import evaluate_intelligence_contract
from services.response_service import store_collection_response


def start_session(db, payload: dict[str, Any]) -> dict[str, Any]:
    assignment = _load_assignment(db, payload)
    survey = _load_survey(db, assignment.survey_id)
    household = db.get(Household, assignment.household_id) if assignment.household_id else None
    enumerator = db.get(EnumeratorProfile, assignment.enumerator_id)
    graph = _survey_graph(survey)
    answers: dict[str, Any] = {}
    timings: dict[str, int] = {}
    order = _expanded_questions(graph, answers)
    current = order[0] if order else None

    row = IntelligenceSession(
        survey_id=survey.survey_id,
        household_id=assignment.household_id,
        enumerator_id=assignment.enumerator_id,
        status="active",
        payload={
            "assignmentId": str(assignment.id),
            "answers": answers,
            "timings": timings,
            "events": [],
            "decisions": [],
            "questionOrder": [item["id"] for item in order],
            "latestIntelligence": None,
            "language": payload.get("language") or "en",
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "sessionId": str(row.id),
        "status": row.status,
        "assignment": _assignment_payload(db, assignment),
        "survey": _survey_payload(survey),
        "household": None if not household else {"id": household.id, "prepop": household.prepopulated},
        "enumerator": None if not enumerator else _enumerator_payload(enumerator),
        "currentQuestion": current,
        "nextQuestionId": current["id"] if current else None,
        "visibleQueue": [item["id"] for item in order],
        "answers": answers,
        "intelligence": None,
        "complete": current is None,
    }


def answer_session(db, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    session = db.get(IntelligenceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collection session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail=f"Collection session is {session.status}")

    data = dict(session.payload or {})
    answers = dict(data.get("answers") or {})
    timings = dict(data.get("timings") or {})
    events = list(data.get("events") or [])
    decisions = list(data.get("decisions") or [])

    question_id = str(payload.get("questionId") or payload.get("question_id") or "")
    if not question_id:
        raise HTTPException(status_code=400, detail="questionId is required")
    value = payload.get("value")
    answers[question_id] = "" if value is None else value
    elapsed_seconds = _elapsed(payload)
    timings[question_id] = max(1, int(round(elapsed_seconds)))

    survey = _load_survey(db, session.survey_id)
    graph = _survey_graph(survey)
    rules = _active_rules_for_answers(db, session.survey_id, answers)
    intelligence = evaluate_intelligence_contract(
        answers=answers,
        active_question_id=question_id,
        speed_mode=_speed_mode(elapsed_seconds, payload),
        elapsed_seconds=elapsed_seconds,
        rules=rules,
        reference=_reference(db, answers),
        enumerator=_enumerator_context(db, session.enumerator_id),
        adaptive_logic=_adaptive_logic(db, session.survey_id),
    )

    order = _expanded_questions(graph, answers)
    next_question = _next_unanswered(order, answers)
    graph_decision = _graph_decision(graph, question_id, answers.get(question_id), next_question)
    if graph_decision:
        intelligence = _with_decision(intelligence, graph_decision)
    elif next_question:
        intelligence = _with_decision(
            intelligence,
            {
                "action": intelligence.get("decision") if intelligence.get("decision") in {"SIMPLIFY", "REORDER"} else "ASK",
                "target": next_question["id"],
                "reason": intelligence.get("reason") or f"asking {next_question['id']} next",
                "params": {},
            },
        )
    else:
        intelligence = _with_decision(
            intelligence,
            {
                "action": "COMPLETE",
                "target": None,
                "reason": "all required questions on the adaptive path have been answered",
                "params": {},
            },
        )

    event = {
        "questionId": question_id,
        "value": answers[question_id],
        "elapsedSeconds": elapsed_seconds,
        "decision": intelligence.get("decision"),
        "nextQuestionId": intelligence.get("nextQuestionId"),
        "confidence": intelligence.get("confidence"),
        "trustLevel": intelligence.get("trustLevel"),
        "reason": intelligence.get("reason"),
    }
    events.append(event)
    decisions.append(intelligence.get("adaptive") or {})

    data.update(
        {
            "answers": answers,
            "timings": timings,
            "events": events,
            "decisions": decisions,
            "questionOrder": [item["id"] for item in order],
            "latestIntelligence": intelligence,
        }
    )
    session.payload = data
    db.commit()

    return {
        "sessionId": str(session.id),
        "status": session.status,
        "accepted": True,
        "answers": answers,
        "currentQuestion": next_question,
        "nextQuestionId": next_question["id"] if next_question else None,
        "visibleQueue": [item["id"] for item in order],
        "intelligence": intelligence,
        "complete": next_question is None,
    }


def complete_session(db, session_id: str) -> dict[str, Any]:
    session = db.get(IntelligenceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collection session not found")
    if session.status == "completed":
        return {"ok": True, "sessionId": str(session.id), "status": session.status, **((session.payload or {}).get("completion") or {})}
    if session.status != "active":
        raise HTTPException(status_code=409, detail=f"Collection session is {session.status}")

    data = dict(session.payload or {})
    answers = dict(data.get("answers") or {})
    intelligence = data.get("latestIntelligence")
    if not answers:
        raise HTTPException(status_code=409, detail="No answers have been captured")
    if not intelligence or intelligence.get("is_verdict") is not True:
        raise HTTPException(status_code=409, detail="No stored verdict is available for this session")

    assignment_id = data.get("assignmentId")
    total_seconds = sum(int(value or 0) for value in (data.get("timings") or {}).values())
    result = store_collection_response(
        db,
        {
            "surveyId": session.survey_id,
            "householdId": session.household_id,
            "enumeratorId": session.enumerator_id,
            "assignmentId": assignment_id,
            "answers": answers,
            "prepopulated": _prepopulated(db, session.household_id),
            "intelligence": intelligence,
            "verdictSource": "session",
            "speedMode": "too-fast" if any(int(v or 0) <= 5 for v in (data.get("timings") or {}).values()) else "normal",
            "elapsedSeconds": min([int(v or 0) for v in (data.get("timings") or {}).values()] or [90]),
            "durationSeconds": total_seconds or None,
            "channel": "collection-session",
        },
    )
    if isinstance(result.get("intelligence"), dict):
        result["intelligence"]["stored"] = True
    data["completion"] = result
    session.payload = data
    session.status = "completed"
    db.commit()
    return {"ok": True, "sessionId": str(session.id), "status": session.status, **result}


def _load_assignment(db, payload: dict[str, Any]) -> Assignment:
    assignment_id = payload.get("assignmentId") or payload.get("assignment_id")
    query = db.query(Assignment).order_by(Assignment.created_at.desc())
    if assignment_id:
        row = db.get(Assignment, assignment_id)
    else:
        survey_id = payload.get("surveyId") or payload.get("survey_id")
        if survey_id:
            query = query.filter(Assignment.survey_id == str(survey_id))
        row = query.filter(Assignment.status == "assigned").first()
    if not row:
        raise HTTPException(status_code=404, detail="No assigned collection work found")
    return row


def _load_survey(db, survey_id: str) -> Survey:
    survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


def _survey_graph(survey: Survey) -> dict[str, Any]:
    graph = survey.question_graph or survey.survey_data or {}
    if not isinstance(graph, dict):
        raise HTTPException(status_code=409, detail="Survey question graph is invalid")
    return graph


def _survey_payload(survey: Survey) -> dict[str, Any]:
    graph = dict(_survey_graph(survey))
    graph.setdefault("id", survey.survey_id)
    graph.setdefault("title", {"en": survey.title})
    graph["status"] = survey.status
    graph["version"] = survey.version
    return graph


def _assignment_payload(db, row: Assignment) -> dict[str, Any]:
    survey = db.query(Survey).filter(Survey.survey_id == row.survey_id).first()
    enumerator = db.get(EnumeratorProfile, row.enumerator_id)
    household = db.get(Household, row.household_id) if row.household_id else None
    return {
        "id": str(row.id),
        "surveyId": row.survey_id,
        "surveyTitle": survey.title if survey else row.survey_id,
        "enumeratorId": row.enumerator_id,
        "enumeratorName": enumerator.name if enumerator else row.enumerator_id,
        "householdId": row.household_id,
        "household": household.prepopulated if household else None,
        "status": row.status,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def _enumerator_payload(row: EnumeratorProfile) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "region": row.region,
        "trustScore": row.trust_score,
        "trustLevel": row.trust_level,
        "trustTrend": row.trust_trend or [],
    }


def _expanded_questions(graph: dict[str, Any], answers: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [dict(node) for node in graph.get("nodes", []) if node.get("type") != "adaptive"]
    occupation = answers.get("occupation")
    branch = (graph.get("branches") or {}).get(str(occupation)) if occupation is not None else None
    if branch:
        branch_question = _branch_question(branch)
        if branch_question and not any(node.get("id") == branch_question["id"] for node in nodes):
            insert_at = next((idx for idx, node in enumerate(nodes) if node.get("id") == "income"), len(nodes))
            nodes = [*nodes[:insert_at], branch_question, *nodes[insert_at:]]
    return nodes


def _branch_question(branch: Any) -> dict[str, Any] | None:
    if not isinstance(branch, dict) or not branch.get("id"):
        return None
    return {
        "id": str(branch["id"]),
        "type": "choice" if branch.get("options") else branch.get("type") or "text",
        "q": branch.get("q") or {"en": str(branch.get("label") or branch["id"])},
        "options": branch.get("options"),
        "rules": branch.get("rules"),
    }


def _next_unanswered(order: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any] | None:
    for question in order:
        qid = question.get("id")
        if qid and qid not in answers:
            return question
    return None


def _graph_decision(graph: dict[str, Any], question_id: str, value: Any, next_question: dict[str, Any] | None) -> dict[str, Any] | None:
    if question_id != "occupation" or next_question is None:
        return None
    branch = (graph.get("branches") or {}).get(str(value))
    if not branch or not isinstance(branch, dict):
        return None
    if next_question.get("id") != branch.get("id"):
        return None
    return {
        "action": "BRANCH",
        "target": next_question["id"],
        "reason": f"branched to {next_question['id']} because occupation={value!r}",
        "params": {"branch": str(value)},
    }


def _with_decision(intelligence: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    next_intelligence = dict(intelligence)
    next_intelligence["decision"] = decision["action"]
    next_intelligence["nextQuestionId"] = decision.get("target")
    next_intelligence["reason"] = decision.get("reason") or next_intelligence.get("reason")
    next_intelligence["adaptive"] = decision
    return next_intelligence


def _active_rules_for_answers(db, survey_id: str, answers: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.query(ValidationRuleRecord).filter(ValidationRuleRecord.survey_id == survey_id).all()
    active: list[dict[str, Any]] = []
    for row in rows:
        params = row.params or {}
        rule = {
            "field": row.field,
            "rule_type": row.rule_type,
            "severity": row.severity,
            "params": params,
            "reason_template": row.reason_template,
        }
        if row.rule_type in {"required", "range", "context"} and params.get("field", row.field) in answers:
            active.append(rule)
        elif row.rule_type == "cross_field" and params.get("if_field") in answers and params.get("then_field") in answers:
            active.append(rule)
        elif row.rule_type == "logic" and params.get("field") in answers:
            active.append(rule)
    return active


def _adaptive_logic(db, survey_id: str) -> list[dict[str, Any]]:
    rows = db.query(AdaptiveLogicRecord).filter(AdaptiveLogicRecord.survey_id == survey_id).all()
    return [{"trigger": row.trigger, "action": row.action, "target": row.target} for row in rows]


def _reference(db, answers: dict[str, Any] | None = None) -> dict[str, Any]:
    from services.reference import resolve_reference

    return resolve_reference(db.query(ReferenceDistribution).all(), answers)


def _enumerator_context(db, enumerator_id: str | None) -> dict[str, Any] | None:
    if not enumerator_id:
        return None
    enumerator = db.get(EnumeratorProfile, enumerator_id)
    if not enumerator:
        return None
    return {"score": enumerator.trust_score, "trend": enumerator.trust_trend or [], "level": enumerator.trust_level}


def _prepopulated(db, household_id: str | None) -> dict[str, Any]:
    household = db.get(Household, household_id) if household_id else None
    return household.prepopulated if household else {}


def _elapsed(payload: dict[str, Any]) -> float:
    try:
        return max(1.0, float(payload.get("elapsedSeconds") or payload.get("elapsed_seconds") or 90))
    except (TypeError, ValueError):
        return 90.0


def _speed_mode(elapsed_seconds: float, payload: dict[str, Any]) -> str:
    explicit = payload.get("speedMode") or payload.get("speed_mode")
    if explicit:
        return str(explicit)
    return "too-fast" if elapsed_seconds <= 5 else "normal"
