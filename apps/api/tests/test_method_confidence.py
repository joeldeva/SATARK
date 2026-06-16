"""Every response carries per-method confidence + proof; the decision follows it."""
from services.intelligence_adapter import evaluate_intelligence_contract as evaluate

EXPECTED_METHODS = {"Completeness", "Range", "Cross-field", "Context", "Behaviour"}


def _by_name(result):
    return {m["name"]: m for m in result["methods"]}


def test_every_method_reports_a_confidence_and_a_method_label():
    r = evaluate(answers={"occupation": "Salaried", "income": 25000, "age": 34}, speed_mode="normal", elapsed_seconds=90)
    assert {m["name"] for m in r["methods"]} == EXPECTED_METHODS
    for m in r["methods"]:
        assert 0.0 <= m["confidence"] <= 100.0
        assert m["method"] and m["reason"]  # proof + the method used
        assert m["flagged"] is False
    # also mirrored on layers
    for layer in r["layers"]:
        assert "confidence" in layer and "method" in layer and "flagged" in layer


def test_genuine_high_confidence_no_flags_green():
    r = evaluate(answers={"occupation": "Salaried", "income": 25000, "age": 34}, speed_mode="normal", elapsed_seconds=90)
    assert r["flaggedBy"] == []
    assert all(m["confidence"] >= 80 for m in r["methods"])
    assert r["trustLevel"] == "Green"


def test_suspicious_flags_specific_methods_with_low_confidence():
    r = evaluate(answers={"occupation": "Unemployed", "income": 200000, "age": 34, "household": 4}, speed_mode="too-fast", elapsed_seconds=4)
    methods = _by_name(r)
    # the methods that should flag are low-confidence; the ones that shouldn't stay high
    assert methods["Cross-field"]["flagged"] and methods["Cross-field"]["confidence"] < 50
    assert methods["Context"]["flagged"] and methods["Context"]["confidence"] < 50
    assert methods["Behaviour"]["flagged"] and methods["Behaviour"]["confidence"] < 50
    assert methods["Completeness"]["confidence"] >= 80 and not methods["Completeness"]["flagged"]
    assert set(r["flaggedBy"]) == {"Cross-field", "Context", "Behaviour"}
    # the decision follows the confidences
    assert r["trustLevel"] == "Red"


def test_range_method_isolates_with_zero_confidence():
    r = evaluate(answers={"occupation": "Salaried", "income": 25000, "age": 200}, speed_mode="normal", elapsed_seconds=90)
    methods = _by_name(r)
    assert methods["Range"]["flagged"] and methods["Range"]["confidence"] <= 10
    assert r["flaggedBy"] == ["Range"]  # only Range fired
    assert not methods["Cross-field"]["flagged"] and not methods["Behaviour"]["flagged"]
