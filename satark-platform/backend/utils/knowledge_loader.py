import json
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    def __init__(self, base_path: str = "knowledge_base"):
        self.base_path = Path(base_path)
        self.surveys = {}
        self.standards = {}

    def load_all(self):
        logger.info("📚 Loading knowledge base...")

        survey_path = self.base_path / "surveys"
        if survey_path.exists():
            for file in survey_path.glob("*.json"):
                domain = file.stem
                try:
                    with open(file, encoding='utf-8') as f:
                        self.surveys[domain] = json.load(f)
                        logger.info(f"✅ Loaded {len(self.surveys[domain].get('questions', []))} questions for {domain}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {file}: {e}")

        standards_path = self.base_path / "standards"
        if standards_path.exists():
            for file in standards_path.glob("*.json"):
                standard_name = file.stem
                try:
                    with open(file, encoding='utf-8') as f:
                        self.standards[standard_name] = json.load(f)
                        logger.info(f"✅ Loaded standard: {standard_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {file}: {e}")

        return self

    def get_questions_by_domain(self, domain: str) -> List[Dict]:
        return self.surveys.get(domain, {}).get("questions", [])

    def get_questions_by_tags(self, tags: List[str], domain: str = None) -> List[Dict]:
        questions = []
        search_surveys = [domain] if domain else self.surveys.keys()
        for d in search_surveys:
            for q in self.surveys.get(d, {}).get("questions", []):
                if any(tag in q.get("tags", []) for tag in tags):
                    questions.append(q)
        return questions

    def get_standard_codes(self, standard: str) -> Dict:
        return self.standards.get(standard, {})
