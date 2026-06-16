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


# Required params per rule_type — a rule that can't be read by the engine is
# worse than no rule (it silently passes), so reject malformed rules on write.
_RULE_PARAM_SCHEMA: dict[str, tuple[str, ...]] = {
    "required": ("field",),
    "range": ("field",),  # plus at least one of min/max (checked below)
    "cross_field": ("if_field", "if_op", "if_value", "then_field", "then_op", "then_value"),
    "context": ("field", "ref_key"),
    "logic": ("field", "requires_field"),
}
_ALLOWED_OPS = {"eq", "ne", "gt", "lt", "gte", "lte", "in", "present"}


def validate_rule_params(rule_type: str, params: Dict[str, Any]) -> None:
    """Raise HTTP 400 if a rule's params can't be evaluated by the engine."""
    params = params or {}
    if rule_type not in _RULE_PARAM_SCHEMA:
        raise HTTPException(status_code=400, detail=f"Unknown rule_type '{rule_type}'")
    missing = [k for k in _RULE_PARAM_SCHEMA[rule_type] if params.get(k) in (None, "")]
    if missing:
        raise HTTPException(status_code=400, detail=f"{rule_type} rule missing params: {missing}")
    if rule_type == "range" and params.get("min") is None and params.get("max") is None:
        raise HTTPException(status_code=400, detail="range rule requires at least one of 'min'/'max'")
    for op_key in ("if_op", "then_op"):
        if op_key in params and params[op_key] not in _ALLOWED_OPS:
            raise HTTPException(status_code=400, detail=f"{op_key}='{params[op_key]}' not in {sorted(_ALLOWED_OPS)}")


def create_validation_rule(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("survey_id", "field", "rule_type"):
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    validate_rule_params(str(payload["rule_type"]), payload.get("params") or {})
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

    # Detect the occupation/income fields SEMANTICALLY (by id/text/tags/code),
    # not by exact id — so LLM-generated surveys (ids like LAB_001, q_income)
    # still get the cross-field + context layers wired and they actually fire.
    occupation_field = _detect_field(nodes, _OCCUPATION_KEYWORDS, code_types={"NCO"})
    income_field = _detect_field(nodes, _INCOME_KEYWORDS)

    if occupation_field and income_field:
        created.append(
            ValidationRuleRecord(
                survey_id=survey_id,
                field=income_field,
                rule_type="cross_field",
                params={
                    "if_field": occupation_field,
                    "if_op": "eq",
                    "if_value": "Unemployed",
                    "then_field": income_field,
                    "then_op": "lte",
                    "then_value": 50000,
                },
                severity="error",
                reason_template="Income cannot contradict unemployed status",
            )
        )
    if income_field:
        created.append(
            ValidationRuleRecord(
                survey_id=survey_id,
                field=income_field,
                rule_type="context",
                params={"field": income_field, "ref_key": "income"},
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


_INCOME_KEYWORDS = ("income", "earning", "earnings", "salary", "salaried", "wage", "wages", "remuneration")
_OCCUPATION_KEYWORDS = ("occupation", "employment status", "employment", "profession", "occupational", "principal activity", "what is your job", "job title")


def _node_searchable(node: Dict[str, Any]) -> str:
    parts = [str(node.get("id") or "")]
    q = node.get("q") or node.get("text")
    if isinstance(q, dict):
        parts.extend(str(v) for v in q.values())
    elif q:
        parts.append(str(q))
    parts.extend(str(t) for t in (node.get("tags") or []))
    for key in ("codeType", "code_type", "standard_code", "category", "subdomain"):
        if node.get(key):
            parts.append(str(node[key]))
    return " ".join(parts).lower()


def _detect_field(nodes: list, keywords: tuple, code_types: set | None = None) -> str | None:
    code_types = code_types or set()
    for node in nodes or []:
        if not node.get("id") or node.get("type") == "adaptive":
            continue
        text = _node_searchable(node)
        if any(kw in text for kw in keywords):
            return str(node.get("id"))
        code = str(node.get("codeType") or node.get("code_type") or node.get("standard_code") or "").upper()
        if code_types and code in code_types:
            return str(node.get("id"))
    return None


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
