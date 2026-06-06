from typing import Dict, List
from uuid import uuid4
from datetime import datetime
from .prompt_parser import PromptParser, ParsedIntent
from .rag_engine import RAGEngine
from .rule_engine import RuleEngine
import logging

logger = logging.getLogger(__name__)


class SurveyGenerator:
    """
    Main survey generation pipeline.
    1. Parse prompt → intent
    2. Get mandatory questions (rules)
    3. Retrieve relevant questions (RAG)
    4. Combine + deduplicate
    5. Order questions
    6. Add validation
    7. Generate skip logic
    8. Package as survey JSON
    """

    def __init__(self, prompt_parser: PromptParser, rag_engine: RAGEngine, rule_engine: RuleEngine):
        self.parser = prompt_parser
        self.rag = rag_engine
        self.rules = rule_engine

    def generate(self, prompt: str, user_id: str = None) -> Dict:
        logger.info(f"🚀 Generating survey: {prompt[:80]}...")

        intent = self.parser.parse(prompt)
        logger.info(f"✅ Intent: domain={intent.domain}, audience={intent.audience}")

        mandatory = self.rules.add_mandatory_questions(intent.domain)
        logger.info(f"✅ Mandatory questions: {len(mandatory)}")

        target_count = intent.num_questions or 10
        needed = max(target_count - len(mandatory), 0)

        search_query = " ".join([intent.domain] + intent.audience + intent.topics)
        retrieved = self.rag.search(
            query=search_query,
            domain=intent.domain,
            tags=intent.topics,
            top_k=needed * 2
        )
        logger.info(f"✅ Retrieved: {len(retrieved)} candidates")

        all_questions = self._combine(mandatory, retrieved, target_count)
        all_questions = self.rules.apply_question_ordering(all_questions)
        all_questions = [self.rules.add_validation_rules(q, intent.domain) for q in all_questions]
        skip_logic = self.rules.generate_skip_logic(all_questions, intent.domain)

        survey = self._package(all_questions, skip_logic, intent, prompt, user_id)
        logger.info(f"✅ Survey ready: {survey['survey_id']} ({len(all_questions)} questions)")
        return survey

    def _combine(self, mandatory: List[Dict], retrieved: List[Dict], target: int) -> List[Dict]:
        combined = mandatory.copy()
        seen_ids = {q["id"] for q in mandatory}

        for q in retrieved:
            if len(combined) >= target:
                break
            if q["id"] in seen_ids:
                continue
            if self._is_duplicate(q, combined):
                continue
            combined.append(q)
            seen_ids.add(q["id"])

        return combined

    def _is_duplicate(self, question: Dict, existing: List[Dict]) -> bool:
        q_text = question["text"].lower()
        q_tags = set(question.get("tags", []))
        for e in existing:
            if q_text == e["text"].lower():
                return True
            if len(q_tags & set(e.get("tags", []))) >= 2:
                return True
        return False

    def _package(self, questions: List[Dict], logic: List[Dict], intent: ParsedIntent, prompt: str, user_id: str) -> Dict:
        survey_id = str(uuid4())

        for i, q in enumerate(questions, 1):
            q["question_number"] = i
            q["display_id"] = f"Q{i}"

        title_parts = []
        if intent.audience:
            title_parts.append(" and ".join(intent.audience).title())
        title_parts.append(intent.domain.title())
        if intent.location_type:
            title_parts.append(f"({intent.location_type.title()})")
        title_parts.append("Survey")

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
                "generation_method": "hybrid_rag_rules",
                "num_questions": len(questions),
                "standards_compliance": {"gsbpm": True, "nss": True}
            },
            "questions": questions,
            "logic": logic,
            "validation_summary": {
                "total_questions": len(questions),
                "required_questions": sum(1 for q in questions if q.get("required")),
                "conditional_questions": len(logic)
            }
        }
