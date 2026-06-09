"""Every assist endpoint must return ``is_verdict=False`` and ``needs_review=True``.

We test the service layer directly (not via TestClient) so the test runs
without spinning up the DB / startup wiring.
"""

from app.intelligence.assist.rag.service import answer, classify_code
from app.intelligence.assist.llm import generate as llm_generate  # noqa: F401  (signature check only)


def test_rag_answer_carries_assist_envelope():
    result = answer("what is rural employment?", bucket="survey_generation", k=3)
    assert result["is_verdict"] is False
    assert result["needs_review"] is True
    assert "sources" in result
    assert "bucket" in result


def test_rag_classify_code_carries_assist_envelope():
    result = classify_code(text="taxi driver", code_type="NCO", k=3)
    assert result["is_verdict"] is False
    assert result["needs_review"] is True
    assert "matches" in result


def test_assist_envelope_in_survey_generator_metadata():
    """survey_generator must emit assist.{is_verdict:False, needs_review:True}."""
    from services.survey_generator import SurveyGenerator
    from services.prompt_parser import PromptParser
    from services.rule_engine import RuleEngine
    from utils.knowledge_loader import KnowledgeBaseLoader
    from pathlib import Path

    data_root = Path(__file__).resolve().parents[3] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_root)).load_all()

    class _Stub:
        def __init__(self, kb):
            self.kb = kb

        def build_index(self):
            return self

        def search(self, query, domain=None, tags=None, top_k=20):
            return self.kb.get_questions_by_domain(domain)[:top_k]

    gen = SurveyGenerator(PromptParser(), _Stub(kb), RuleEngine(kb))
    survey = gen.generate("A survey for rural women about healthcare access with 6 questions", "tester")
    assist_meta = (survey.get("metadata") or {}).get("assist") or {}
    assert assist_meta.get("is_verdict") is False
    assert assist_meta.get("needs_review") is True
