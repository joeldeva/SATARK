import copy
import logging
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from .prompt_parser import ParsedIntent, PromptParser
from .rag_engine import RAGEngine
from .rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class SurveyGenerator:
    """Deterministic survey generation pipeline."""

    def __init__(self, prompt_parser: PromptParser, rag_engine: RAGEngine, rule_engine: RuleEngine, llm_planner=None):
        self.parser = prompt_parser
        self.rag = rag_engine
        self.rules = rule_engine
        self.llm_planner = llm_planner

    def generate(self, prompt: str, user_id: str = None) -> Dict:
        intent = self.llm_planner.plan(prompt) if self.llm_planner else self.parser.parse(prompt)
        target_count = intent.num_questions or 10

        mandatory = self.rules.add_mandatory_questions(intent.domain)
        draft_questions = self._llm_draft_questions(intent)
        needed = max(target_count - len(mandatory) - len(draft_questions), 0)
        search_query = " ".join([intent.domain] + intent.audience + intent.topics)
        retrieved = self.rag.search(
            query=search_query,
            domain=intent.domain,
            tags=intent.topics,
            top_k=max(needed * 3, target_count),
        )

        questions = self._combine(mandatory, draft_questions, retrieved, target_count)
        questions = self.rules.apply_question_ordering(questions)
        questions = [self.rules.add_validation_rules(question, intent.domain) for question in questions]
        logic = self.rules.generate_skip_logic(questions, intent.domain)

        survey = self._package(questions, logic, intent, prompt, user_id)
        logger.info("Survey generated: %s (%s questions)", survey["survey_id"], len(questions))
        return survey

    def _llm_draft_questions(self, intent: ParsedIntent) -> List[Dict]:
        if intent.planner != "local_llm":
            return []
        return [copy.deepcopy(question) for question in intent.draft_questions]

    def _combine(self, *sources_and_target) -> List[Dict]:
        *sources, target = sources_and_target
        combined = []
        seen_ids = set()
        seen_texts = set()

        for source in sources:
            for question in source:
                if len(combined) >= target:
                    return combined
                text_key = question["text"].strip().lower()
                if question["id"] in seen_ids or text_key in seen_texts:
                    continue
                combined.append(copy.deepcopy(question))
                seen_ids.add(question["id"])
                seen_texts.add(text_key)

        return combined

    def _package(self, questions: List[Dict], logic: List[Dict], intent: ParsedIntent, prompt: str, user_id: str) -> Dict:
        survey_id = str(uuid4())

        for index, question in enumerate(questions, 1):
            question["question_number"] = index
            question["display_id"] = f"Q{index}"

        domain_label = "Labour and Employment" if intent.domain == "labour" else intent.domain.title()
        title_parts = []
        if intent.audience and intent.audience != ["general"]:
            title_parts.append(" and ".join(intent.audience).title())
        title_parts.append(domain_label)
        if intent.location_type:
            title_parts.append(f"({intent.location_type.title()})")
        title_parts.append("Survey")

        required_count = sum(1 for question in questions if question.get("required"))
        return {
            "survey_id": survey_id,
            "title": " ".join(title_parts),
            "description": f"Generated from: {prompt}",
            "domain": intent.domain,
            "target_audience": intent.audience,
            "location_type": intent.location_type,
            "languages": intent.language,
            "version": "1.0",
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id or "system",
            "metadata": {
                "source_prompt": prompt,
                "generation_method": (
                    "local_llm_intent_planner_rules_keyword_retrieval"
                    if intent.planner == "local_llm"
                    else "deterministic_rules_keyword_retrieval"
                ),
                "llm": {
                    "provider": "ollama" if intent.planner == "local_llm" else "none",
                    "model": intent.planner_model,
                    "role": "intent_and_draft_question_planning",
                    "privacy": "local_inference_no_external_api",
                    "confidence": intent.planner_confidence,
                    "reason": intent.planner_reason,
                },
                "question_count": len(questions),
                "standards_compliance": {"gsbpm": True, "nss": True},
                "engine_trace": [
                    {
                        "step": "intent_planning",
                        "output": {
                            "domain": intent.domain,
                            "topics": intent.topics,
                            "planner": intent.planner,
                            "model": intent.planner_model,
                            "reason": intent.planner_reason,
                            "draft_questions": len(intent.draft_questions),
                        },
                    },
                    {"step": "retrieve", "output": {"selected_questions": len(questions)}},
                    {"step": "rules", "output": {"required_questions": required_count, "logic_rules": len(logic)}},
                ],
            },
            "questions": questions,
            "logic": logic,
            "validation_summary": {
                "total_questions": len(questions),
                "required_questions": required_count,
                "conditional_questions": len(logic),
            },
        }
