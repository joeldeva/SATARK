"""Phase 3 — adaptive questioning: all five actions fire WITH a reason.

BRANCH / SKIP come from adaptive_logic rows; SIMPLIFY / REORDER from behaviour
signals (fatigue / dropout); ASK is the default. Every decision carries a
plain-language reason — a statistician can read exactly why.
"""
from app.intelligence.adaptive.adaptive_engine import (
    DROPOUT_REORDER,
    FATIGUE_SIMPLIFY,
    AdaptiveEngine,
)
from app.intelligence.schemas import ValidationContext
from app.intelligence.verdict.behaviour_engine import BehaviourSignals
from services.intelligence_adapter import evaluate_intelligence_contract

ENGINE = AdaptiveEngine()


def _signals(fatigue=0, dropout=0):
    return BehaviourSignals(engagement=100, fatigue=fatigue, dropout_risk=dropout, quality=100)


def _ctx(answers):
    return ValidationContext(answers=answers, rules=[], reference={}, paradata={})


def test_branch_fires_with_reason():
    logic = [{"action": "BRANCH", "trigger": {"field": "occupation", "value": "Student"},
              "target": {"qid": "institution", "branch": "Student"}}]
    d = ENGINE.decide(_ctx({"occupation": "Student"}), _signals(), adaptive_logic=logic, last_qid="occupation")
    assert d["action"] == "BRANCH"
    assert d["target"] == "institution"
    assert "student" in d["reason"].lower() and d["reason"]


def test_skip_fires_with_reason():
    logic = [{"action": "SKIP", "trigger": {"field": "occupation", "value": "Salaried"},
              "target": {"qid": "land"}}]
    d = ENGINE.decide(_ctx({"occupation": "Salaried"}), _signals(), adaptive_logic=logic, last_qid="occupation")
    assert d["action"] == "SKIP"
    assert d["target"] == "land"
    assert "skipped" in d["reason"].lower() and "salaried" in d["reason"].lower()


def test_simplify_fires_on_high_fatigue_with_reason():
    d = ENGINE.decide(_ctx({"income": 1}), _signals(fatigue=FATIGUE_SIMPLIFY + 5), adaptive_logic=[], last_qid="income")
    assert d["action"] == "SIMPLIFY"
    assert "fatigue" in d["reason"].lower()
    assert str(FATIGUE_SIMPLIFY + 5) in d["reason"]


def test_reorder_fires_on_high_dropout_with_reason():
    # dropout takes priority over fatigue
    d = ENGINE.decide(_ctx({"income": 1}), _signals(dropout=DROPOUT_REORDER + 5), adaptive_logic=[], last_qid="income")
    assert d["action"] == "REORDER"
    assert "dropout" in d["reason"].lower()
    assert str(DROPOUT_REORDER + 5) in d["reason"]


def test_ask_is_the_default_with_reason():
    d = ENGINE.decide(_ctx({"income": 25000}), _signals(), adaptive_logic=[], last_qid="income")
    assert d["action"] == "ASK"
    assert d["reason"]


def test_branch_flows_through_the_orchestrator():
    """BRANCH surfaces on the scored result's adaptive block (one pipeline)."""
    logic = [{"action": "BRANCH", "trigger": {"field": "occupation", "value": "Student"},
              "target": {"qid": "institution", "branch": "Student"}}]
    result = evaluate_intelligence_contract(
        answers={"occupation": "Student"},
        active_question_id="occupation",
        adaptive_logic=logic,
        speed_mode="normal",
        elapsed_seconds=20,
    )
    assert result["adaptive"]["action"] == "BRANCH"
    assert result["decision"] == "BRANCH"
    assert result["adaptive"]["reason"]
