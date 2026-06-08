from pathlib import Path

from services.prompt_parser import PromptParser
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from utils.knowledge_loader import KnowledgeBaseLoader


class SimpleRAG:
    def __init__(self, kb):
        self.kb = kb

    def search(self, query, domain=None, tags=None, top_k=20):
        return self.kb.get_questions_by_domain(domain)[:top_k]


def test_generated_survey_is_assist_only_and_needs_review():
    data_path = Path(__file__).resolve().parents[3] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_path)).load_all()
    generator = SurveyGenerator(PromptParser(), SimpleRAG(kb), RuleEngine(kb))

    survey = generator.generate("Design a household employment survey with income validation", "sdrd")
    assist = survey["metadata"]["assist"]

    assert assist["needs_review"] is True
    assert assist["is_verdict"] is False
    assert assist["role"] == "survey_generation_draft"
