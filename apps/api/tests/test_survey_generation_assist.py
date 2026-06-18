from pathlib import Path

from services.prompt_parser import ParsedIntent
from services.prompt_parser import PromptParser
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from utils.knowledge_loader import KnowledgeBaseLoader


class SimpleRAG:
    def __init__(self, kb):
        self.kb = kb

    def search(self, query, domain=None, tags=None, top_k=20):
        questions = self.kb.get_questions_by_domain(domain)[:top_k]
        if any(tag in {"laptop", "keyboard", "repair"} for tag in tags or []):
            questions = [
                {
                    "id": "rag_keyboard_service",
                    "domain": "household",
                    "subdomain": "question_bank",
                    "text": "Which repair channel was used for the laptop keyboard issue?",
                    "type": "single_choice",
                    "category": "core",
                    "tags": ["laptop", "keyboard", "repair"],
                    "options": [{"value": "authorized", "label": "Authorized service centre"}, {"value": "local", "label": "Local repair shop"}],
                    "validation": {},
                    "required": True,
                    "source": "rag_question_bank",
                },
                {
                    "id": "rag_keyboard_downtime",
                    "domain": "household",
                    "subdomain": "question_bank",
                    "text": "How many days was the laptop unavailable due to the keyboard issue?",
                    "type": "number",
                    "category": "core",
                    "tags": ["laptop", "keyboard", "downtime"],
                    "options": [],
                    "validation": {"type": "range", "min": 0, "max": 365},
                    "required": True,
                    "source": "rag_question_bank",
                },
                *questions,
            ]
        return questions[:top_k]


def test_generated_survey_is_assist_only_and_needs_review():
    data_path = Path(__file__).resolve().parents[3] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_path)).load_all()
    generator = SurveyGenerator(PromptParser(), SimpleRAG(kb), RuleEngine(kb))

    survey = generator.generate("Design a household employment survey with income validation", "sdrd")
    assist = survey["metadata"]["assist"]

    assert assist["needs_review"] is True
    assert assist["is_verdict"] is False
    assert assist["role"] == "survey_generation_draft"


class FailingPlanner:
    model = "free-model"

    def plan(self, prompt: str):
        raise RuntimeError("provider unavailable")


def test_generation_falls_back_to_full_draft_when_llm_fails():
    data_path = Path(__file__).resolve().parents[3] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_path)).load_all()
    generator = SurveyGenerator(PromptParser(), SimpleRAG(kb), RuleEngine(kb), llm_planner=FailingPlanner())

    survey = generator.generate(
        "Generate a household employment survey for Tamil Nadu with income, migration, assets and validation. Make 12 questions.",
        "sdrd",
    )

    assert len(survey["questions"]) >= 10
    assert survey["metadata"]["llm"]["provider"] == "none"
    assert survey["metadata"]["llm"]["model"] == "free-model"
    assert survey["metadata"]["assist"]["is_verdict"] is False


class KeyboardPlanner:
    model = "gemma2:2b"

    def plan(self, prompt: str):
        return ParsedIntent(
            domain="household",
            audience=["general"],
            location_type="urban",
            topics=["laptop", "keyboard", "repair", "chennai"],
            num_questions=7,
            special_requirements=["validation"],
            language=["en"],
            planner="local_llm",
            planner_model=self.model,
            planner_confidence=95,
            planner_reason="Prompt asks for a laptop keyboard issue survey in Chennai.",
            assist_framework="test",
            draft_questions=[
                {
                    "id": "llm_keyboard_happened",
                    "domain": "household",
                    "subdomain": "local_llm_prompt_specific",
                    "text": "Have you experienced any issues with your laptop keyboard in Chennai?",
                    "type": "single_choice",
                    "category": "screening",
                    "tags": ["laptop", "keyboard"],
                    "options": [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}],
                    "validation": {},
                    "required": True,
                },
                {
                    "id": "llm_keyboard_type",
                    "domain": "household",
                    "subdomain": "local_llm_prompt_specific",
                    "text": "What type of laptop keyboard issue did you experience?",
                    "type": "single_choice",
                    "category": "core",
                    "tags": ["laptop", "keyboard", "issue"],
                    "options": [{"value": "typing", "label": "Typing issue"}, {"value": "keys", "label": "Keys not working"}],
                    "validation": {},
                    "required": True,
                },
                {
                    "id": "llm_keyboard_cost",
                    "domain": "household",
                    "subdomain": "local_llm_prompt_specific",
                    "text": "What was the approximate cost of repairing the laptop keyboard?",
                    "type": "number",
                    "category": "sensitive",
                    "tags": ["laptop", "keyboard", "repair", "cost"],
                    "options": [],
                    "validation": {"type": "range", "min": 0, "max": 1000000},
                    "required": True,
                },
            ],
        )


def test_llm_draft_questions_stay_prompt_specific_before_generic_bank_questions():
    data_path = Path(__file__).resolve().parents[3] / "data"
    kb = KnowledgeBaseLoader(base_path=str(data_path)).load_all()
    generator = SurveyGenerator(PromptParser(), SimpleRAG(kb), RuleEngine(kb), llm_planner=KeyboardPlanner())

    survey = generator.generate(
        "Build a 7 question survey about laptop keyboard issues in Chennai with cost and satisfaction.",
        "sdrd",
    )

    texts = [question["text"].lower() for question in survey["questions"]]
    sources = [question.get("source") for question in survey["questions"]]
    assert len(texts) == 7
    assert texts[0].startswith("have you experienced any issues with your laptop keyboard")
    assert any("repairing the laptop keyboard" in text for text in texts)
    assert any(source == "local_llm_draft" for source in sources)
    assert any(source in {"rag_question_bank", "satark_rag_pattern_bank"} for source in sources)
    assert not any(text in {"what is the respondent's age?", "what is your age?"} for text in texts[:3])
