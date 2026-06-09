"""CRUD for validation_rules and adaptive_logic — pure SQLAlchemy.

Same import boundary as survey_service: no imports from app.intelligence.verdict.*.
The verdict lane reads these rows at collection time from its own DAL.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.platform import ValidationRuleRecord
from models.survey import AdaptiveLogicRecord


# ---------------- validation_rules ----------------

def list_validation_rules(db: Session, survey_id: str | None) -> List[Dict[str, Any]]:
    query = db.query(ValidationRuleRecord)
    if survey_id:
        query = query.filter(ValidationRuleRecord.survey_id == survey_id)
    return [_rule_to_dict(r) for r in query.all()]


def create_validation_rule(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("survey_id", "field", "rule_type"):
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    row = ValidationRuleRecord(
        survey_id=str(payload["survey_id"]),
        field=str(payload["field"]),
        rule_type=str(payload["rule_type"]),
        params=payload.get("params") or {},
        severity=str(payload.get("severity") or "error"),
        reason_template=str(payload.get("reason_template") or ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _rule_to_dict(row)


def ensure_default_validation_rules(db: Session, survey_id: str, question_graph: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    existing = db.query(ValidationRuleRecord).filter(ValidationRuleRecord.survey_id == survey_id).count()
    if existing:
        return []

    graph = question_graph or {}
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    fields = {str(node.get("id")) for node in nodes or [] if node.get("id") and node.get("type") != "adaptive"}
    created: list[ValidationRuleRecord] = []

    for node in nodes or []:
        field = str(node.get("id") or "")
        if not field or node.get("type") == "adaptive":
            continue
        created.append(
            ValidationRuleRecord(
                survey_id=survey_id,
                field=field,
                rule_type="required",
                params={"field": field},
                severity="error",
                reason_template=f"{field} is required",
            )
        )
        range_rule = (node.get("rules") or {}).get("range")
        if node.get("type") == "number" and isinstance(range_rule, list) and len(range_rule) == 2:
            created.append(
                ValidationRuleRecord(
                    survey_id=survey_id,
                    field=field,
                    rule_type="range",
                    params={"field": field, "min": range_rule[0], "max": range_rule[1]},
                    severity="error",
                    reason_template=f"{field} must be inside the configured range",
                )
            )

    if {"occupation", "income"}.issubset(fields):
        created.append(
            ValidationRuleRecord(
                survey_id=survey_id,
                field="income",
                rule_type="cross_field",
                params={
                    "if_field": "occupation",
                    "if_op": "eq",
                    "if_value": "Unemployed",
                    "then_field": "income",
                    "then_op": "lte",
                    "then_value": 50000,
                },
                severity="error",
                reason_template="Income cannot contradict unemployed status",
            )
        )
    if "income" in fields:
        created.append(
            ValidationRuleRecord(
                survey_id=survey_id,
                field="income",
                rule_type="context",
                params={"field": "income", "ref_key": "income"},
                severity="warning",
                reason_template="Income should be inside the regional reference band",
            )
        )

    for row in created:
        db.add(row)
    db.commit()
    return [_rule_to_dict(row) for row in created]


def update_validation_rule(db: Session, rule_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = db.query(ValidationRuleRecord).filter(ValidationRuleRecord.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    for key in ("field", "rule_type", "severity", "reason_template"):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    if "params" in payload:
        row.params = payload["params"] or {}
    db.commit()
    db.refresh(row)
    return _rule_to_dict(row)


def delete_validation_rule(db: Session, rule_id: str) -> Dict[str, Any]:
    row = db.query(ValidationRuleRecord).filter(ValidationRuleRecord.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    db.delete(row)
    db.commit()
    return {"deleted": rule_id}


def _rule_to_dict(row: ValidationRuleRecord) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "survey_id": row.survey_id,
        "field": row.field,
        "rule_type": row.rule_type,
        "params": row.params or {},
        "severity": row.severity,
        "reason_template": row.reason_template,
    }


# ---------------- adaptive_logic ----------------

def list_adaptive_logic(db: Session, survey_id: str | None) -> List[Dict[str, Any]]:
    query = db.query(AdaptiveLogicRecord)
    if survey_id:
        query = query.filter(AdaptiveLogicRecord.survey_id == survey_id)
    return [_adaptive_to_dict(r) for r in query.all()]


def create_adaptive_logic(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("survey_id", "trigger", "action", "target"):
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    row = AdaptiveLogicRecord(
        survey_id=str(payload["survey_id"]),
        trigger=payload["trigger"],
        action=str(payload["action"]),
        target=payload["target"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _adaptive_to_dict(row)


def update_adaptive_logic(db: Session, rule_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = db.query(AdaptiveLogicRecord).filter(AdaptiveLogicRecord.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Adaptive logic not found")
    if "trigger" in payload and payload["trigger"] is not None:
        row.trigger = payload["trigger"]
    if "action" in payload and payload["action"] is not None:
        row.action = str(payload["action"])
    if "target" in payload and payload["target"] is not None:
        row.target = payload["target"]
    db.commit()
    db.refresh(row)
    return _adaptive_to_dict(row)


def delete_adaptive_logic(db: Session, rule_id: str) -> Dict[str, Any]:
    row = db.query(AdaptiveLogicRecord).filter(AdaptiveLogicRecord.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Adaptive logic not found")
    db.delete(row)
    db.commit()
    return {"deleted": rule_id}


def _adaptive_to_dict(row: AdaptiveLogicRecord) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "survey_id": row.survey_id,
        "trigger": row.trigger,
        "action": row.action,
        "target": row.target,
    }
