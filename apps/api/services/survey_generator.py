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
        intent = self._plan_intent(prompt)
        target_count = intent.num_questions or 10

        draft_questions = self._llm_draft_questions(intent)
        search_query = " ".join([intent.domain] + intent.audience + intent.topics)
        if draft_questions:
            gemma_quota = max(1, (target_count + 1) // 2)
            rag_quota = max(target_count - min(len(draft_questions), gemma_quota), 0)
            draft_questions = draft_questions[:gemma_quota]
            retrieved = self.rag.search(
                query=search_query,
                domain=intent.domain,
                tags=intent.topics,
                top_k=max(rag_quota * 4, target_count),
            ) if rag_quota else []
            retrieved = self._filter_relevant_retrieved(retrieved, intent, rag_quota)
            questions = self._combine(draft_questions, retrieved, target_count)
            questions = self._fill_missing_questions(questions, intent, target_count, topic_first=True)
        else:
            mandatory = self.rules.add_mandatory_questions(intent.domain)
            needed = max(target_count - len(mandatory), 0)
            retrieved = self.rag.search(
                query=search_query,
                domain=intent.domain,
                tags=intent.topics,
                top_k=max(needed * 3, target_count),
            )
            questions = self._combine(mandatory, retrieved, target_count)
            questions = self._fill_missing_questions(questions, intent, target_count)
            questions = self.rules.apply_question_ordering(questions)
        questions = [self.rules.add_validation_rules(question, intent.domain) for question in questions]
        logic = self.rules.generate_skip_logic(questions, intent.domain)

        survey = self._package(questions, logic, intent, prompt, user_id)
        logger.info("Survey generated: %s (%s questions)", survey["survey_id"], len(questions))
        return survey

    _LLM_PLANNERS = ("local_llm", "openrouter", "prompt_fallback")

    def _plan_intent(self, prompt: str) -> ParsedIntent:
        if not self.llm_planner:
            return self.parser.parse(prompt)
        try:
            return self.llm_planner.plan(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM planner failed; using deterministic survey generation fallback: %s", exc)
            intent = self.parser.parse(prompt)
            intent.planner = "prompt_fallback"
            intent.planner_model = getattr(self.llm_planner, "model", None)
            intent.planner_confidence = 76
            intent.planner_reason = "Cloud LLM assist was unavailable; SATARK generated prompt-specific draft questions locally."
            intent.assist_framework = "bounded_llm_fallback_prompt_specific"
            intent.draft_questions = self._prompt_fallback_draft_questions(intent)
            return intent

    def _llm_draft_questions(self, intent: ParsedIntent) -> List[Dict]:
        if intent.planner not in self._LLM_PLANNERS:
            return []
        questions = []
        for question in intent.draft_questions:
            draft = copy.deepcopy(question)
            draft.setdefault("source", "local_llm_draft")
            draft.setdefault("subdomain", "local_llm_prompt_specific")
            questions.append(draft)
        filtered = self._filter_prompt_specific_drafts(questions, intent)
        if filtered:
            return filtered
        if self._core_subject_topics(intent):
            return self._prompt_fallback_draft_questions(intent)
        return questions

    def _filter_prompt_specific_drafts(self, questions: List[Dict], intent: ParsedIntent) -> List[Dict]:
        core_subject_topics = self._core_subject_topics(intent)
        if not core_subject_topics:
            return questions
        relevant = []
        for question in questions:
            text = str(question.get("text") or "").lower()
            tags = {str(tag).lower() for tag in question.get("tags", [])}
            is_generic = self._is_generic_demographic(text, tags)
            topic_hit = bool(core_subject_topics & tags or any(topic in text for topic in core_subject_topics))
            if topic_hit and not is_generic:
                relevant.append(question)
        return relevant

    def _prompt_fallback_draft_questions(self, intent: ParsedIntent) -> List[Dict]:
        topic = ", ".join(intent.topics[:3]) if intent.topics else intent.domain
        topic_slug = "_".join(str(part).lower().replace(" ", "_") for part in intent.topics[:2]) or intent.domain
        base_tags = intent.topics[:5] or [intent.domain]
        templates = [
            ("screening", "single_choice", f"Has the respondent directly experienced an issue related to {topic}?", ["Yes", "No", "Do not know"]),
            ("core", "text", f"What type of issue or situation did the respondent face related to {topic}?", []),
            ("core", "number", f"How often did this issue related to {topic} occur in the reference period?", []),
            ("sensitive", "number", f"What approximate cost, income loss, or time burden was caused by {topic}?", []),
            ("core", "text", f"Where or through which service channel was support sought for {topic}?", []),
            ("follow_up", "single_choice", f"Was any official record, receipt, or evidence available for {topic}?", ["Yes", "No", "Not applicable"]),
        ]
        questions = []
        for index, (category, question_type, text, options) in enumerate(templates, 1):
            questions.append({
                "id": f"prompt_{index}_{topic_slug}"[:64],
                "domain": intent.domain,
                "subdomain": "prompt_specific_fallback",
                "text": text,
                "type": question_type,
                "category": category,
                "tags": base_tags,
                "options": [{"value": option.lower().replace(" ", "_"), "label": option} for option in options],
                "validation": {"type": "range", "min": 0} if question_type == "number" else {},
                "required": category in {"screening", "core"},
                "routing": None,
                "standard_code": None,
                "source": "bounded_prompt_fallback",
                "audience": intent.audience,
            })
        return questions

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

    def _filter_relevant_retrieved(self, questions: List[Dict], intent: ParsedIntent, target_count: int) -> List[Dict]:
        if target_count <= 0:
            return []
        topics = {topic.lower() for topic in intent.topics or [] if len(topic) > 2}
        core_subject_topics = self._core_subject_topics(intent)
        distinctive_topics = self._distinctive_topics(intent)
        relevant = []

        for question in questions:
            text = str(question.get("text") or "").lower()
            raw_tags = {str(tag).lower() for tag in question.get("tags", [])}
            tags = raw_tags - topics if "uploaded_source" in raw_tags else raw_tags
            is_generic = self._is_generic_demographic(text, tags)
            if core_subject_topics:
                strong_hit = bool(core_subject_topics & tags or any(topic in text for topic in core_subject_topics))
            else:
                strong_hit = bool(distinctive_topics and (distinctive_topics & tags or any(topic in text for topic in distinctive_topics)))
            weak_hit_count = len(topics & tags) + sum(1 for topic in topics if topic in text)
            topic_hit = strong_hit if core_subject_topics else (strong_hit or weak_hit_count >= 2)
            if topic_hit and not is_generic:
                relevant.append(question)

        return relevant[:target_count]

    def _distinctive_topics(self, intent: ParsedIntent) -> set[str]:
        topics = {topic.lower() for topic in intent.topics or [] if len(topic) > 2}
        weak_topics = {
            "cost", "issue", "issues", "frequency", "satisfaction", "validation", "survey",
            "question", "questions", "household", "income", "amount", "type", "yes", "no",
            "service", "centre", "center", "repair", "repairs", "used",
        }
        return {topic for topic in topics if topic not in weak_topics and len(topic) > 4}

    def _core_subject_topics(self, intent: ParsedIntent) -> set[str]:
        location_topics = {
            "chennai", "tamil", "nadu", "india", "urban", "rural", "district", "state", "area",
        }
        return self._distinctive_topics(intent) - location_topics

    def _is_generic_demographic(self, text: str, tags: set[str]) -> bool:
        generic_tags = {"age", "gender", "marital", "education", "name", "demographic"}
        return bool(tags & generic_tags) or any(
            word in text for word in ["age", "gender", "marital status", "education"]
        )

    def _fill_missing_questions(self, questions: List[Dict], intent: ParsedIntent, target_count: int, topic_first: bool = False) -> List[Dict]:
        if len(questions) >= target_count:
            return questions

        generated = list(questions)
        seen_ids = {question["id"] for question in generated}
        templates = self._fallback_templates(intent, topic_first=topic_first)
        for template in templates:
            if len(generated) >= target_count:
                break
            if template["id"] in seen_ids:
                continue
            generated.append(template)
            seen_ids.add(template["id"])
        return generated

    def _fallback_templates(self, intent: ParsedIntent, topic_first: bool = False) -> List[Dict]:
        domain = intent.domain or "household"
        topics = intent.topics or []
        location = intent.location_type or "survey area"
        topic_text = ", ".join(topics[:3]) or domain
        topic_base = [
            ("fb_topic_experience", f"What is the respondent's direct experience related to {topic_text}?", "text", "core", topics[:4] or [domain]),
            ("fb_topic_frequency", f"How often did the respondent experience an issue related to {topic_text}?", "single_choice", "core", [*topics[:3], "frequency"]),
            ("fb_topic_cost", f"What approximate cost, loss, or time burden was caused by {topic_text}?", "number", "sensitive", [*topics[:3], "cost"]),
            ("fb_topic_cause", f"What was the main reason or cause reported for {topic_text}?", "single_choice", "core", [*topics[:3], "cause"]),
            ("fb_topic_resolution", f"What action was taken to resolve or report the issue related to {topic_text}?", "single_choice", "follow_up", [*topics[:3], "resolution"]),
            ("fb_topic_evidence", f"Can the enumerator verify the response about {topic_text} using records, observation, or respondent evidence?", "single_choice", "follow_up", [*topics[:3], "validation"]),
        ]
        demographic_base = [
            ("fb_dem_name", "What is the full name of the primary respondent?", "text", "demographic", ["name"]),
            ("fb_dem_age", "What is the respondent's age?", "number", "demographic", ["age"]),
            ("fb_dem_gender", "What is the respondent's gender?", "single_choice", "demographic", ["gender"]),
            ("fb_household_size", "How many usual members live in this household?", "number", "core", ["household"]),
            ("fb_location", f"Which district or locality in the {location} is this household located in?", "text", "core", ["location"]),
            ("fb_occupation", "What is the respondent's main occupation or current work status?", "single_choice", "core", ["occupation", "employment"]),
            ("fb_income", "What was the household's approximate monthly income last month?", "number", "sensitive", ["income"]),
            ("fb_education", "What is the highest level of education completed by the respondent?", "single_choice", "core", ["education"]),
            ("fb_migration", "Has any household member migrated for work or study in the last 12 months?", "single_choice", "social", ["migration"]),
            ("fb_assets", "Does the household own any major productive assets or durable goods?", "single_choice", "core", ["assets"]),
            ("fb_verification", "Can the enumerator verify the response using household records or observation?", "single_choice", "follow_up", ["validation"]),
            ("fb_topic", f"What is the household's main issue or experience related to {topic_text}?", "text", "core", topics[:4] or [domain]),
        ]
        base = topic_base + demographic_base if topic_first else demographic_base + topic_base
        questions = []
        for qid, text, question_type, category, tags in base:
            options = []
            if question_type == "single_choice":
                options = self._default_options(qid)
            validation = {}
            if question_type == "number":
                validation = {"type": "range", "min": 0, "max": 120 if "age" in tags else 10000000}
            questions.append({
                "id": qid,
                "domain": domain,
                "subdomain": "deterministic_fallback",
                "text": text,
                "type": question_type,
                "category": category,
                "tags": tags,
                "options": options,
                "validation": validation,
                "required": category in {"demographic", "core"},
                "routing": None,
                "standard_code": "NCO" if "occupation" in tags else None,
                "source": "satark_rag_pattern_bank" if topic_first and qid.startswith("fb_topic") else "satark_deterministic_fallback",
                "audience": intent.audience,
            })
        return questions

    def _default_options(self, qid: str) -> List[Dict]:
        options = {
            "fb_dem_gender": ["Male", "Female", "Other", "Prefer not to say"],
            "fb_occupation": ["Salaried", "Self-employed", "Farmer", "Unemployed", "Student", "Other"],
            "fb_education": ["No formal education", "Primary", "Secondary", "Higher secondary", "Graduate and above"],
            "fb_migration": ["Yes", "No"],
            "fb_assets": ["Yes", "No"],
            "fb_verification": ["Verified", "Partially verified", "Not verified"],
        }.get(qid, ["Yes", "No"])
        return [{"value": option.lower().replace(" ", "_"), "label": option} for option in options]

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
                    f"{intent.planner}_intent_planner_rules_keyword_retrieval"
                    if intent.planner in self._LLM_PLANNERS
                    else "deterministic_rules_keyword_retrieval"
                ),
                "llm": {
                    "provider": (
                        "openrouter" if intent.planner == "openrouter"
                        else "ollama" if intent.planner == "local_llm"
                        else "none"
                    ),
                    "model": intent.planner_model,
                    "role": "intent_and_draft_question_planning",
                    "privacy": (
                        "online_openrouter" if intent.planner == "openrouter"
                        else "local_inference_no_external_api"
                    ),
                    "confidence": intent.planner_confidence,
                    "reason": intent.planner_reason,
                },
                "assist": {
                    "needs_review": True,
                    "is_verdict": False,
                    "model": intent.planner_model,
                    "role": "survey_generation_draft",
                    "framework": intent.assist_framework,
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
                            "assist_framework": intent.assist_framework,
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
