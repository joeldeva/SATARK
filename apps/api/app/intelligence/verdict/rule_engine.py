"""
Deterministic rule engine — verdict lane.

Takes a ValidationContext (answers + rules + reference data) and emits
one CheckResult per rule.  No I/O, no model, no randomness.

Rule types (stored in validation_rules.params):
  range        {"field", "min", "max"}
  required     {"field"}
  cross_field  {"if_field", "if_op", "if_value", "then_field", "then_op", "then_value"}
  context      {"field", "ref_key"}   — uses reference distribution band p05/p95
  logic        {"field", "requires_field"}   — skip-logic consistency

Malformed answers produce a FAIL with a reason, never an unhandled exception.
"""
from app.intelligence.schemas import CheckResult, Status, ValidationContext

# ── Operator table ────────────────────────────────────────────────────────────
_OPS: dict = {
    "eq":      lambda a, b: a == b,
    "ne":      lambda a, b: a != b,
    "gt":      lambda a, b: _num(a) is not None and _num(a) > _num(b),
    "lt":      lambda a, b: _num(a) is not None and _num(a) < _num(b),
    "gte":     lambda a, b: _num(a) is not None and _num(a) >= _num(b),
    "lte":     lambda a, b: _num(a) is not None and _num(a) <= _num(b),
    "in":      lambda a, b: a in b,
    "present": lambda a, _: _present(a),
}

_LAYER_FOR = {
    "range":       "rule",
    "required":    "rule",
    "cross_field": "cross_field",
    "context":     "context",
    "logic":       "logic",
}


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _present(v) -> bool:
    return v not in (None, "", [])


class RuleEngine:
    """
    Pure, stateless rule evaluator.
    Instantiate once; call .run() per response.
    """

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        results: list[CheckResult] = []
        for rule in ctx.rules:
            rt = rule.get("rule_type")
            handler = getattr(self, f"_check_{rt}", None)
            if handler is None:
                continue
            try:
                results.append(handler(rule, ctx))
            except Exception as exc:  # noqa: BLE001
                # Safety net: malformed rule definition never crashes the pipeline
                results.append(CheckResult(
                    layer=_LAYER_FOR.get(rt, "rule"),
                    field=rule.get("params", {}).get("field"),
                    status=Status.FAIL,
                    severity="error",
                    reason=f"Rule evaluation error for rule_type={rt}: {exc}",
                    recommended_action="review",
                ))
        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    def _mk(
        self,
        rule: dict,
        status: Status,
        field: str | None,
        reason: str,
        confidence: float | None = None,
    ) -> CheckResult:
        if confidence is None:
            confidence = 100.0 if status is Status.PASS else 55.0 if status is Status.WARN else 10.0
        return CheckResult(
            layer=_LAYER_FOR.get(rule.get("rule_type"), "rule"),
            field=field,
            status=status,
            severity=rule.get("severity", "error"),
            reason=reason,
            recommended_action=(
                "re_interview" if status is Status.FAIL else
                "review"       if status is Status.WARN else
                None
            ),
            confidence=max(0.0, min(100.0, confidence)),
        )

    # ── Check implementations ─────────────────────────────────────────────────

    def _check_range(self, rule: dict, ctx: ValidationContext) -> CheckResult:
        p = rule["params"]
        f = p["field"]
        v = _num(ctx.answers.get(f))
        if v is None:
            return self._mk(rule, Status.FAIL, f, f"{f} is not a number")
        lo, hi = p.get("min"), p.get("max")
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            span = (hi - lo) if (lo is not None and hi is not None and hi > lo) else max(abs(v), 1)
            overflow = max((lo - v) if lo is not None else 0, (v - hi) if hi is not None else 0, 0) / span
            confidence = max(0.0, 40.0 - overflow * 40.0)
            return self._mk(
                rule, Status.FAIL, f,
                f"{f}={v:g} outside allowed range [{lo}, {hi}]",
                confidence=confidence,
            )
        return self._mk(rule, Status.PASS, f, f"{f}={v:g} within range", confidence=100.0)

    def _check_required(self, rule: dict, ctx: ValidationContext) -> CheckResult:
        f = rule["params"]["field"]
        ok = _present(ctx.answers.get(f))
        return self._mk(
            rule,
            Status.PASS if ok else Status.FAIL,
            f,
            f"{f} provided" if ok else f"{f} is required but missing",
        )

    def _check_cross_field(self, rule: dict, ctx: ValidationContext) -> CheckResult:
        p = rule["params"]
        if_val   = ctx.answers.get(p["if_field"])
        then_val = ctx.answers.get(p["then_field"])

        # Only evaluate when the antecedent holds — no spurious failures
        if not _OPS[p["if_op"]](if_val, p["if_value"]):
            return self._mk(
                rule, Status.PASS, p["then_field"],
                f"cross-field check not triggered ({p['if_field']}={if_val!r})",
            )

        ok = _OPS[p["then_op"]](then_val, p["then_value"])
        if ok:
            return self._mk(rule, Status.PASS, p["then_field"], "cross-field consistent")
        return self._mk(
            rule, Status.FAIL, p["then_field"],
            f"{p['then_field']}={then_val!r} contradicts "
            f"{p['if_field']}='{if_val}'",
        )

    def _check_context(self, rule: dict, ctx: ValidationContext) -> CheckResult:
        p = rule["params"]
        f = p["field"]
        v = _num(ctx.answers.get(f))
        band = ctx.reference.get(p["ref_key"], {})
        lo, hi, median = band.get("p05"), band.get("p95"), band.get("median")
        stratum = band.get("stratum", "all")
        if v is None or lo is None or hi is None:
            return self._mk(rule, Status.PASS, f, "no reference band available — skipped")
        median_txt = f", median {median:g}" if isinstance(median, (int, float)) else ""
        span = (hi - lo) if hi > lo else 1
        if v > hi:
            overflow = (v - hi) / span
            confidence = max(10.0, 60.0 - overflow * 50.0)
            return self._mk(
                rule, Status.WARN, f,
                f"{f}={v:g} is above the 95th-percentile ceiling {hi:g} for {stratum}{median_txt}",
                confidence=confidence,
            )
        if v < lo:
            underflow = (lo - v) / span
            confidence = max(10.0, 60.0 - underflow * 50.0)
            return self._mk(
                rule, Status.WARN, f,
                f"{f}={v:g} is below the 5th-percentile floor {lo:g} for {stratum}{median_txt}",
                confidence=confidence,
            )
        center = median if isinstance(median, (int, float)) else (lo + hi) / 2
        half = max(hi - center, center - lo, 1)
        deviation = min(abs(v - center) / half, 1.0)
        confidence = 100.0 - 30.0 * deviation
        return self._mk(rule, Status.PASS, f, f"{f}={v:g} is within the reference band [{lo:g}-{hi:g}] for {stratum}", confidence=confidence)

    def _check_logic(self, rule: dict, ctx: ValidationContext) -> CheckResult:
        p = rule["params"]
        f   = p["field"]
        req = p["requires_field"]
        if _present(ctx.answers.get(f)) and not _present(ctx.answers.get(req)):
            return self._mk(
                rule, Status.FAIL, f,
                f"{f} answered but prerequisite {req} is empty (skip-logic break)",
            )
        return self._mk(rule, Status.PASS, f, "skip-logic consistent")
