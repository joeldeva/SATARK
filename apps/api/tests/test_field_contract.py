from services.intelligence_adapter import evaluate_intelligence_contract


def test_intelligence_answer_keeps_frontend_field_contract():
    result = evaluate_intelligence_contract(
        answers={"age": "34", "occupation": "Salaried", "income": "25000", "household": "4"},
        active_question_id="income",
        speed_mode="normal",
        elapsed_seconds=90,
    )

    required = {
        "confidence",
        "trustLevel",
        "decision",
        "nextQuestionId",
        "reason",
        "layers",
        "scores",
        "breakdown",
        "suggestion",
        "stored",
    }
    assert required <= set(result)
    assert {"engagement", "fatigue", "dropout", "quality"} <= set(result["scores"])
    assert {"validation", "fraud", "evidence", "behaviour"} <= set(result["breakdown"])
    assert [layer["layer"] for layer in result["layers"]] == [
        "Completeness",
        "Range",
        "Cross-field",
        "Context",
        "Behaviour",
    ]
    assert result["is_verdict"] is True
