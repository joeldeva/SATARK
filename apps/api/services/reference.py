"""Per-stratum reference-distribution resolver (data-loading seam).

The verdict engines receive a flat ``{key: {p05, median, p95, stratum, params}}``
band per field. This resolver picks the right *stratum* for each key from the
response's own answers (e.g. income band for Unemployed vs Salaried households),
so the Context layer is sharp and its reason names the stratum — without changing
any engine code or the "Context is advisory (WARN)" contract.

Stratum match is value-based (``occupation_is``) so it works regardless of the
survey's field ids — emp-2026's ``occupation`` and an LLM survey's ``LAB_001``
both resolve the same way as long as the answer value is "Unemployed".
"""
from __future__ import annotations

from typing import Any


def resolve_reference(rows, answers: dict[str, Any] | None) -> dict[str, Any]:
    answers = answers or {}
    answer_values = {str(v).strip().lower() for v in answers.values() if v is not None}
    by_key: dict[str, list] = {}
    for row in rows:
        by_key.setdefault(row.key, []).append(row)
    return {key: _band(_pick(candidates, answer_values, answers)) for key, candidates in by_key.items()}


def _pick(candidates, answer_values: set[str], answers: dict[str, Any]):
    best, best_score = None, -1
    for row in candidates:
        match = (row.params or {}).get("match") or {}
        score = 0
        applicable = True
        for mk, mv in match.items():
            if mk == "occupation_is":
                if str(mv).strip().lower() in answer_values:
                    score += 2
                else:
                    applicable = False
                    break
            else:
                if str(answers.get(mk)).strip().lower() == str(mv).strip().lower():
                    score += 1
                else:
                    applicable = False
                    break
        if not applicable:
            continue
        if score > best_score:
            best, best_score = row, score
    return best or candidates[0]


def _band(row) -> dict[str, Any]:
    return {
        "stratum": row.stratum,
        "p05": row.p05,
        "median": row.median,
        "p95": row.p95,
        "params": row.params or {},
    }
