from services.intelligence_adapter import evaluate_intelligence_contract


def test_genuine_response_lands_green_above_90():
    result = evaluate_intelligence_contract(
        answers={"occupation": "Salaried", "income": "25000", "age": "34", "household": "4"},
        speed_mode="normal",
        elapsed_seconds=85,
    )

    assert result["trustLevel"] == "Green"
    assert result["confidence"] >= 90


def test_suspicious_response_lands_red_below_50_with_reasons():
    result = evaluate_intelligence_contract(
        answers={
            "occupation": "Unemployed",
            "income": "200000",
            "age": "34",
            "q1": "99",
            "q2": "99",
            "q3": "99",
            "q4": "99",
        },
        speed_mode="too-fast",
        elapsed_seconds=4,
    )

    reasons = " ".join(result["native_trust"]["reasons"]).lower()
    assert result["trustLevel"] == "Red"
    assert result["confidence"] < 50
    assert "contradicts" in reasons
    assert "median" in reasons or "pace" in reasons


def test_minimal_suspicious_response_lands_red_below_50():
    result = evaluate_intelligence_contract(
        answers={
            "occupation": "Unemployed",
            "income": "200000",
            "age": "34",
            "household": "4",
        },
        speed_mode="too-fast",
        elapsed_seconds=4,
    )

    reasons = " ".join(result["native_trust"]["reasons"]).lower()
    assert result["trustLevel"] == "Red"
    assert result["confidence"] < 50
    assert "contradicts" in reasons
    assert "median" in reasons or "pace" in reasons
