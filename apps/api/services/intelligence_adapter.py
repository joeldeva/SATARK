from __future__ import annotations

from typing import Any

from app.intelligence.orchestrator import IntelligenceInput, orchestrator


DEFAULT_RULES = [
    {
        "field": "income",
        "rule_type": "cross_field",
        "severity": "error",
        "params": {
            "if_field": "occupation",
            "if_op": "eq",
            "if_value": "Unemployed",
            "then_field": "income",
            "then_op": "lte",
            "then_value": 50000,
        },
    },
    {
        "field": "age",
        "rule_type": "range",
        "severity": "error",
        "params": {"field": "age", "min": 18, "max": 95},
    },
    {
        "field": "household",
        "rule_type": "range",
        "severity": "error",
        "params": {"field": "household", "min": 1, "max": 30},
    },
    {
        "field": "income",
        "rule_type": "context",
        "severity": "warning",
        "params": {"field": "income", "ref_key": "income"},
    },
]

DEFAULT_REFERENCE = {
    "income": {
        "stratum": "Tamil Nadu urban households",
        "p05": 6000,
        "median": 22000,
        "p95": 80000,
    }
}


def evaluate_intelligence_contract(
    answers: dict[str, Any],
    active_question_id: str | None = None,
    persona: str = "genuine",
    speed_mode: str = "normal",
    elapsed_seconds: float = 0,
    rules: list[dict[str, Any]] | None = None,
    reference: dict[str, Any] | None = None,
    enumerator: dict[str, Any] | None = None,
    adaptive_logic: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the deterministic verdict lane and preserve the existing frontend API shape."""

    normalized_answers = {key: _scalar(key, value) for key, value in (answers or {}).items()}
    paradata = _paradata(normalized_answers, speed_mode, elapsed_seconds)
    numeric_fields = [
        key
        for key, value in normalized_answers.items()
        if key in {"age", "income", "household"} and _is_numeric(value)
    ]

    result = orchestrator.process_answer(
        IntelligenceInput(
            answers=normalized_answers,
            rules=rules or _active_rules(normalized_answers),
            reference=reference or DEFAULT_REFERENCE,
            paradata=paradata,
            numeric_fields=numeric_fields,
            evidence_present=True,
            enumerator=enumerator,
            adaptive_logic=adaptive_logic or [],
            last_qid=active_question_id,
        )
    )

    trust = result.trust
    layers = _layers(result.validation)
    suggestion = _code_suggestion(normalized_answers.get("occupation", "")) if active_question_id == "occupation" else None

    # Per-method proof: which methods ran, each one's confidence in this answer,
    # and which ones flagged it. The overall decision is driven by these scores.
    methods = [
        {
            "name": layer["layer"],
            "method": layer["method"],
            "status": layer["status"],
            "confidence": layer["confidence"],
            "flagged": layer["flagged"],
            "reason": layer["reason"],
        }
        for layer in layers
    ]
    flagged_by = [m["name"] for m in methods if m["flagged"]]

    return {
        "confidence": trust["confidence"],
        "trustLevel": trust["risk_level"],
        "decision": result.adaptive.get("action", "ASK"),
        "nextQuestionId": result.adaptive.get("target"),
        "reason": _primary_reason(trust, result.adaptive),
        "layers": layers,
        "methods": methods,
        "flaggedBy": flagged_by,
        "scores": {
            "engagement": result.behaviour.get("engagement", 100),
            "fatigue": result.behaviour.get("fatigue", 0),
            "dropout": result.behaviour.get("dropout_risk", 0),
            "quality": result.behaviour.get("quality", trust["confidence"]),
        },
        "breakdown": trust["breakdown"],
        "suggestion": suggestion,
        "stored": False,
        "is_verdict": trust.get("is_verdict", True),
        "recommendation": trust.get("recommendation"),
        "fraud_signals": trust.get("fraud_signals", []),
        "events": result.events,
        "adaptive": result.adaptive,
        "enumerator_update": result.enumerator_update,
        "native_trust": trust,
    }


def _paradata(answers: dict[str, Any], speed_mode: str, elapsed_seconds: float) -> dict[str, Any]:
    answered_count = max(len(answers), 1)
    seconds = float(elapsed_seconds or 0)
    if speed_mode == "too-fast":
        seconds = seconds or 4
    elif seconds <= 0:
        seconds = 90

    return {
        "total_seconds": max(1, int(round(seconds * answered_count))),
        "question_timings": {key: max(1, int(round(seconds))) for key in answers},
        "correction_count": 0 if speed_mode == "too-fast" else 1,
        "back_nav_count": 0,
        "pauses": 0,
    }


def _active_rules(answers: dict[str, Any]) -> list[dict[str, Any]]:
    active = []
    for rule in DEFAULT_RULES:
        field = rule.get("field")
        rule_type = rule.get("rule_type")
        if rule_type == "cross_field":
            params = rule.get("params", {})
            if params.get("if_field") in answers and params.get("then_field") in answers:
                active.append(rule)
        elif rule_type == "context":
            params = rule.get("params", {})
            if params.get("field") in answers:
                active.append(rule)
        elif field in answers:
            active.append(rule)
    return active


_METHOD_LABEL = {
    "Completeness": "Required-field presence check",
    "Range": "Bounds & type-range check",
    "Cross-field": "Cross-field consistency rule",
    "Context": "Per-stratum reference band + Bayesian anomaly",
    "Behaviour": "Paradata fraud-signal analysis",
}


def _layers(validation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {
        "Completeness": {"layer": "Completeness", "status": "pass", "reason": "Required responses are present", "confidence": 100.0},
        "Range": {"layer": "Range", "status": "pass", "reason": "Numeric answers are inside permitted ranges", "confidence": 100.0},
        "Cross-field": {"layer": "Cross-field", "status": "pass", "reason": "Cross-field rules are consistent", "confidence": 100.0},
        "Context": {"layer": "Context", "status": "pass", "reason": "Values are within reference distributions", "confidence": 100.0},
        "Behaviour": {"layer": "Behaviour", "status": "pass", "reason": "Response behaviour is consistent with expected survey pace", "confidence": 100.0},
    }
    priority = {"fail": 2, "warn": 1, "pass": 0}

    for check in validation:
        label = _label_for_check(check)
        current = buckets[label]
        status = "warn" if check.get("status") == "warning" else check.get("status", "pass")
        # the method's confidence in this answer = the weakest (worst) check it ran
        current["confidence"] = min(current["confidence"], float(check.get("confidence", 100.0)))
        if priority.get(status, 0) >= priority.get(current["status"], 0):
            current.update({"status": status, "reason": check.get("reason") or current["reason"]})

    for label, bucket in buckets.items():
        bucket["confidence"] = round(bucket["confidence"], 1)
        bucket["method"] = _METHOD_LABEL[label]
        bucket["flagged"] = bucket["status"] != "pass"

    return list(buckets.values())


def _label_for_check(check: dict[str, Any]) -> str:
    layer = check.get("layer")
    field = check.get("field")
    if layer == "cross_field":
        return "Cross-field"
    if layer == "context":
        return "Context"
    if layer == "behaviour":
        return "Behaviour"
    if field == "name":
        return "Completeness"
    return "Range"


def _primary_reason(trust: dict[str, Any], adaptive: dict[str, Any]) -> str:
    reasons = trust.get("reasons") or []
    if reasons:
        return str(reasons[0])
    return str(adaptive.get("reason") or "All validation layers are currently passing")


def _code_suggestion(raw_value: Any) -> dict[str, Any] | None:
    value = str(raw_value or "").strip().lower()
    if not value:
        return None
    local = {
        "driver": ("8322", "NCO", "Auto-rickshaw / taxi driver"),
        "farmer": ("6111", "NCO", "Field crop / vegetable grower"),
        "developer": ("2511", "NCO", "Software developer"),
        "software": ("2511", "NCO", "Software developer"),
    }
    for needle, (code, code_type, label) in local.items():
        if needle in value:
            return {
                "code": code,
                "type": code_type,
                "label": label,
                "confidence": 92,
                "source": "Local",
                "reason": f"Matched '{needle}' to {code_type} {code}",
            }
    return None


def _scalar(key: str, value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    if key in {"age", "income", "household"} and _is_numeric(value):
        number = float(value)
        return int(number) if number.is_integer() else number
    return value


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
