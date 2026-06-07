import copy
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SurveyRules:
    mandatory_demographics: List[str]
    question_order: List[str]
    validation_rules: Dict
    skip_logic: Dict


class RuleEngine:
    def __init__(self, knowledge_base_loader):
        self.kb = knowledge_base_loader

    def get_rules_for_domain(self, domain: str) -> SurveyRules:
        validation_rules = self.kb.standards.get("validation_rules", {})
        domain_key = "employment" if domain == "labour" else domain
        domain_rules = validation_rules.get("domains", {}).get(domain_key, {})

        return SurveyRules(
            mandatory_demographics=domain_rules.get("required_fields", ["age", "gender", "location"]),
            question_order=["demographic", "screening", "core", "social", "sensitive", "follow_up"],
            validation_rules=domain_rules.get("validation", {}),
            skip_logic=domain_rules.get("skip_logic", {}),
        )

    def add_mandatory_questions(self, domain: str) -> List[Dict]:
        rules = self.get_rules_for_domain(domain)
        mandatory = []
        seen = set()

        for tag in rules.mandatory_demographics:
            matches = self.kb.get_questions_by_tags([tag, "demographic"], domain)
            for question in matches:
                if question["id"] not in seen:
                    mandatory.append(question)
                    seen.add(question["id"])
                    break

        if len(mandatory) < 2:
            for question in self.kb.get_questions_by_tags(["demographic"]):
                if question["id"] not in seen:
                    mandatory.append(question)
                    seen.add(question["id"])
                if len(mandatory) >= 3:
                    break

        return mandatory[:4]

    def apply_question_ordering(self, questions: List[Dict]) -> List[Dict]:
        order = {
            "demographic": 0,
            "screening": 1,
            "core": 2,
            "social": 3,
            "sensitive": 4,
            "follow_up": 5,
        }
        return sorted(questions, key=lambda question: order.get(question.get("category", "core"), 2))

    def add_validation_rules(self, question: Dict, domain: str) -> Dict:
        question = copy.deepcopy(question)
        rules = self.get_rules_for_domain(domain)
        validation = question.get("validation") or {}

        if "age" in question.get("tags", []):
            age_range = rules.validation_rules.get("age_range", [0, 120])
            validation.update({"min": age_range[0], "max": age_range[1], "type": "range", "required": True})

        if "income" in question.get("tags", []):
            income_range = rules.validation_rules.get("income_range", [0, 10000000])
            validation.update({"min": income_range[0], "max": income_range[1], "type": "range"})

        question["validation"] = {k: v for k, v in validation.items() if v is not None}
        if question.get("category") in {"demographic", "screening"}:
            question["required"] = True

        return question

    def generate_skip_logic(self, questions: List[Dict], domain: str) -> List[Dict]:
        logic_rules = []
        question_ids = {question["id"] for question in questions}

        for question in questions:
            routing = question.get("routing") or {}
            show_if = routing.get("show_if")
            skip_to = routing.get("skip_to")
            if show_if:
                logic_rules.append({
                    "source_question": question["id"],
                    "condition": show_if,
                    "action": "show_if",
                    "target_question": question["id"],
                })
            if skip_to and skip_to in question_ids:
                logic_rules.append({
                    "source_question": question["id"],
                    "condition": routing.get("condition", "answered"),
                    "action": "skip",
                    "target_question": skip_to,
                })

        return logic_rules
