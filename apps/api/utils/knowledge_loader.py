import copy
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.surveys: Dict[str, Dict[str, List[Dict]]] = {}
        self.standards: Dict[str, Dict] = {}
        self._seen_question_ids: set[str] = set()

    def load_all(self):
        logger.info("Loading knowledge base from %s", self.base_path)
        self._load_question_bank()
        self._load_survey_files()
        self._load_standards()
        total = sum(len(s.get("questions", [])) for s in self.surveys.values())
        logger.info("Knowledge base ready: %s domains, %s questions", len(self.surveys), total)
        return self

    def _load_question_bank(self):
        bank_file = self.base_path / "question_bank" / "question_bank.json"
        if not bank_file.exists():
            logger.warning("Question bank not found: %s", bank_file)
            return

        with bank_file.open(encoding="utf-8") as handle:
            records = json.load(handle)

        for record in records:
            question = self._normalize_question(record)
            if question:
                self._add_question(question)

    def _load_survey_files(self):
        survey_path = self.base_path / "knowledge_base" / "surveys"
        if not survey_path.exists():
            return

        for file in sorted(survey_path.glob("*.json")):
            domain = "labour" if file.stem == "employment" else file.stem
            try:
                with file.open(encoding="utf-8") as handle:
                    survey_data = json.load(handle)
                for record in survey_data.get("questions", []):
                    question = self._normalize_question(record, default_domain=domain)
                    if question:
                        self._add_question(question)
            except Exception as exc:
                logger.error("Failed to load %s: %s", file, exc)

    def _load_standards(self):
        standards_path = self.base_path / "knowledge_base" / "standards"
        if not standards_path.exists():
            return

        for file in sorted(standards_path.glob("*.json")):
            try:
                with file.open(encoding="utf-8") as handle:
                    self.standards[file.stem] = json.load(handle)
            except Exception as exc:
                logger.error("Failed to load standard %s: %s", file, exc)

    def _normalize_question(self, record: Dict, default_domain: Optional[str] = None) -> Optional[Dict]:
        question_id = str(record.get("id", "")).strip()
        if not question_id:
            return None

        text = record.get("text", record.get("question", ""))
        if isinstance(text, dict):
            text = text.get("en") or next(iter(text.values()), "")
        text = str(text).strip()
        if not text:
            return None

        domain = str(record.get("domain") or default_domain or "general").strip().lower()
        if domain == "employment":
            domain = "labour"

        validation = self._normalize_validation(record.get("validation") or {})
        options = self._normalize_options(record.get("options") or [])
        category = self._normalize_category(str(record.get("category") or "core"))

        return {
            "id": question_id,
            "domain": domain,
            "subdomain": record.get("subdomain"),
            "text": text,
            "type": record.get("type", "text"),
            "category": category,
            "tags": [str(tag).lower() for tag in record.get("tags", record.get("keywords", []))],
            "options": options,
            "validation": validation,
            "required": bool(record.get("required", validation.get("required", False))),
            "routing": copy.deepcopy(record.get("routing")),
            "standard_code": record.get("standard_code") or record.get("code"),
            "source": record.get("source") or record.get("standard"),
            "audience": record.get("audience", []),
        }

    def _normalize_options(self, options: Iterable[Dict]) -> List[Dict]:
        normalized = []
        for option in options:
            label = option.get("label", "")
            if isinstance(label, dict):
                label = label.get("en") or next(iter(label.values()), "")
            normalized.append({
                "value": str(option.get("value", "")),
                "label": str(label),
                "standard_code": option.get("standard_code") or option.get("code"),
            })
        return normalized

    def _normalize_validation(self, validation: Dict) -> Dict:
        return {
            "min": validation.get("min", validation.get("min_value")),
            "max": validation.get("max", validation.get("max_value")),
            "pattern": validation.get("pattern"),
            "required": validation.get("required", False),
            "type": validation.get("type") or ("range" if "min_value" in validation or "max_value" in validation else None),
        }

    def _normalize_category(self, category: str) -> str:
        category = category.lower()
        if category in {"income", "economic"}:
            return "sensitive"
        if category in {"followup", "follow-up"}:
            return "follow_up"
        if category in {"employment_status", "healthcare_access", "general_health"}:
            return "screening"
        if category not in {"demographic", "screening", "core", "sensitive", "social", "follow_up"}:
            return "core"
        return category

    def _add_question(self, question: Dict):
        if question["id"] in self._seen_question_ids:
            return
        self._seen_question_ids.add(question["id"])
        self.surveys.setdefault(question["domain"], {"questions": []})["questions"].append(question)

    def get_questions_by_domain(self, domain: Optional[str]) -> List[Dict]:
        if not domain:
            return self.get_all_questions()
        domain = "labour" if domain == "employment" else domain
        return [copy.deepcopy(q) for q in self.surveys.get(domain, {}).get("questions", [])]

    def get_questions_by_tags(self, tags: List[str], domain: Optional[str] = None) -> List[Dict]:
        wanted = {tag.lower() for tag in tags}
        domains = self._candidate_domains(domain)
        questions = []
        for d in domains:
            for question in self.surveys.get(d, {}).get("questions", []):
                question_tags = {tag.lower() for tag in question.get("tags", [])}
                if wanted & question_tags or question.get("category") in wanted:
                    questions.append(copy.deepcopy(question))
        return questions

    def get_all_questions(self) -> List[Dict]:
        questions = []
        for survey_data in self.surveys.values():
            questions.extend(copy.deepcopy(survey_data.get("questions", [])))
        return questions

    def get_standard_codes(self, standard: str) -> Dict:
        return self.standards.get(standard, {})

    def _candidate_domains(self, domain: Optional[str]) -> List[str]:
        if not domain:
            return list(self.surveys.keys())
        domain = "labour" if domain == "employment" else domain
        candidates = ["demographic", domain]
        if domain != "household":
            candidates.append("household")
        return [candidate for candidate in candidates if candidate in self.surveys]
