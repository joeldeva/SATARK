from pathlib import Path

from services.prompt_parser import PromptParser
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from utils.knowledge_loader import KnowledgeBaseLoader


class SimpleRAG:
    def __init__(self, kb):
        self.kb = kb

    def build_index(self):
        return self

    def search(self, query, domain=None, tags=None, top_k=20):
        candidates = self.kb.get_questions_by_domain(domain)
        return candidates[:top_k]


def test_core_pipeline():
    data_path = Path(__file__).resolve().parents[2] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_path)).load_all()
    generator = SurveyGenerator(PromptParser(), SimpleRAG(kb), RuleEngine(kb))

    survey = generator.generate(
        "A survey for rural women about healthcare access with 8 questions",
        "test_user",
    )

    assert survey["domain"] == "health"
    assert survey["questions"]
    assert len(survey["questions"]) <= 8
    assert survey["validation_summary"]["total_questions"] == len(survey["questions"])


if __name__ == "__main__":
    test_core_pipeline()
    print("SUCCESS - SATARK core pipeline working")
