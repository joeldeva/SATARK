"""Phase 4 — full deterministic validation matrix.

Deterministic rules are not "98% accurate" — they are 100% correct on the
defined matrix. Each layer is exercised in isolation AND in combination through
the single scoring entry point (evaluate_intelligence_contract -> orchestrator).
"""
from services.intelligence_adapter import evaluate_intelligence_contract

REQUIRED_NAME = {"field": "name", "rule_type": "required", "severity": "error", "params": {"field": "name"}}


def _layers(result):
    return {layer["layer"]: layer for layer in result["layers"]}


def _statuses(result):
    return {name: layer["status"] for name, layer in _layers(result).items()}


def _fails(result):
    return {name for name, layer in _layers(result).items() if layer["status"] == "fail"}


# 1 — genuine baseline: all five layers pass, confidence >= 90, Green
def test_case01_genuine_all_pass_green():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": 25000, "age": 34},
        speed_mode="normal", elapsed_seconds=90,
    )
    assert _fails(r) == set()
    assert all(s == "pass" for s in _statuses(r).values())
    assert r["trustLevel"] == "Green"
    assert r["confidence"] >= 90


# 2 — age out of range (high)
def test_case02_age_200_range_fail():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": 25000, "age": 200},
        speed_mode="normal", elapsed_seconds=90,
    )
    s = _statuses(r)
    assert s["Range"] == "fail"
    assert s["Cross-field"] == "pass" and s["Behaviour"] == "pass" and s["Completeness"] == "pass"


# 3 — age out of range (negative)
def test_case03_age_negative_range_fail():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": 25000, "age": -5},
        speed_mode="normal", elapsed_seconds=90,
    )
    assert _statuses(r)["Range"] == "fail"


# 4 — required field blank -> Completeness fail
def test_case04_required_blank_completeness_fail():
    r = evaluate_intelligence_contract(
        answers={"name": "", "age": 34},
        rules=[REQUIRED_NAME, {"field": "age", "rule_type": "range", "severity": "error", "params": {"field": "age", "min": 18, "max": 95}}],
        speed_mode="normal", elapsed_seconds=90,
    )
    assert _statuses(r)["Completeness"] == "fail"
    assert _statuses(r)["Range"] == "pass"


# 5 — Unemployed + ₹2,00,000, NORMAL speed -> Cross-field is the only hard fail; Behaviour passes
def test_case05_crossfield_only_behaviour_pass():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Unemployed", "income": 200000},
        speed_mode="normal", elapsed_seconds=90,
    )
    assert _fails(r) == {"Cross-field"}
    assert _statuses(r)["Behaviour"] == "pass"


# 6 — genuine answers but 4s/question -> Behaviour is the only fail; Cross-field passes
def test_case06_behaviour_only_crossfield_pass():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": 25000, "age": 34},
        speed_mode="too-fast", elapsed_seconds=4,
    )
    assert _fails(r) == {"Behaviour"}
    assert _statuses(r)["Cross-field"] == "pass"


# 7 — Salaried + ₹5,00,000 -> Context WARN (amber), not a hard fail
def test_case07_context_warn_not_fail():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": 500000},
        speed_mode="normal", elapsed_seconds=90,
    )
    assert _statuses(r)["Context"] == "warn"
    assert _fails(r) == set()


# 8 — Unemployed + ₹2,00,000 + too-fast + no corrections -> conf < 50 Red, >=2 fails, flag.created
def test_case08_combined_red_flag():
    r = evaluate_intelligence_contract(
        answers={"occupation": "Unemployed", "income": 200000, "age": 34, "household": 4},
        speed_mode="too-fast", elapsed_seconds=4,
    )
    assert r["trustLevel"] == "Red"
    assert r["confidence"] < 50
    assert len(_fails(r)) >= 2
    assert "flag.created" in r["events"]
    fail_reasons = [layer["reason"] for layer in r["layers"] if layer["status"] == "fail"]
    assert len(fail_reasons) >= 2 and all(fail_reasons)


# 9 — identical answer to every question -> straight-lining signal fires
def test_case09_straight_lining():
    r = evaluate_intelligence_contract(
        answers={"q1": "yes", "q2": "yes", "q3": "yes", "q4": "yes"},
        speed_mode="normal", elapsed_seconds=90,
    )
    reasons = " ".join(r["native_trust"]["reasons"]).lower()
    assert "straight-lining" in reasons
    assert _statuses(r)["Behaviour"] == "fail"


# 10 — every result row carries a non-null reason string (across all cases)
def test_case10_every_layer_has_a_reason():
    cases = [
        {"occupation": "Salaried", "income": 25000, "age": 34},
        {"occupation": "Unemployed", "income": 200000, "age": 34, "household": 4},
        {"occupation": "Salaried", "income": 500000},
    ]
    for answers in cases:
        r = evaluate_intelligence_contract(answers=answers, speed_mode="normal", elapsed_seconds=90)
        for layer in r["layers"]:
            assert isinstance(layer["reason"], str) and layer["reason"].strip()
        for reason in r["native_trust"]["reasons"]:
            assert isinstance(reason, str) and reason.strip()
