from typing import Dict, List
from dataclasses import dataclass, field


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
        domain_rules = validation_rules.get("domains", {}).get(domain, {})

        return SurveyRules(
            mandatory_demographics=domain_rules.get("required_fields", ["age", "gender"]),
            question_order=["demographic", "screening", "core", "sensitive"],
            validation_rules=domain_rules.get("validation", {}),
            skip_logic=domain_rules.get("skip_logic", {})
        )

    def add_mandatory_questions(self, domain: str) -> List[Dict]:
        mandatory = []
        demographics = self.kb.get_questions_by_tags(["demographic"], domain)
        if demographics:
            mandatory.extend(demographics[:3])

        rules = self.get_rules_for_domain(domain)
        for field_name in rules.mandatory_demographics:
            if field_name not in ["age", "gender"]:
                questions = self.kb.get_questions_by_tags([field_name], domain)
                if questions:
                    mandatory.append(questions[0])

        return mandatory

    def apply_question_ordering(self, questions: List[Dict]) -> List[Dict]:
        categorized = {"demographic": [], "screening": [], "core": [], "sensitive": []}

        for q in questions:
            cat = q.get("category", "core")
            categorized.setdefault(cat, categorized["core"]).append(q)

        return (
            categorized["demographic"] +
            categorized["screening"] +
            categorized["core"] +
            categorized["sensitive"]
        )

    def add_validation_rules(self, question: Dict, domain: str) -> Dict:
        rules = self.get_rules_for_domain(domain)

        if "age" in question.get("tags", []):
            age_range = rules.validation_rules.get("age_range", [0, 120])
            question["validation"] = {"min": age_range[0], "max": age_range[1], "type": "range"}

        if question.get("tags", [""])[0] in rules.mandatory_demographics:
            question["required"] = True

        return question

    def generate_skip_logic(self, questions: List[Dict], domain: str) -> List[Dict]:
        rules = self.get_rules_for_domain(domain)
        logic_rules = []

        for i, q in enumerate(questions):
            q_tags = q.get("tags", [])
            for condition, action in rules.skip_logic.items():
                if condition in q_tags:
                    target_tags = action[0].replace("skip_to_", "").split("_")
                    for j, target_q in enumerate(questions[i+1:], start=i+1):
                        if any(tag in target_q.get("tags", []) for tag in target_tags):
                            logic_rules.append({
                                "source_question": q["id"],
                                "condition": f"{q['display_id']} == 'No'",
                                "action": "skip",
                                "target_question": target_q["id"]
                            })
                            break

        return logic_rules
