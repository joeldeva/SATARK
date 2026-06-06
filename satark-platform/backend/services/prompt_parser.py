import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class ParsedIntent:
    domain: str
    audience: List[str]
    location_type: Optional[str]
    topics: List[str]
    num_questions: Optional[int]
    special_requirements: List[str]
    language: List[str] = field(default_factory=lambda: ["en"])


class PromptParser:
    """
    Regex + keyword based prompt parser.
    No external NLP dependency - fully offline, zero-latency.
    """

    def __init__(self):
        self.domain_keywords = {
            "employment": ["job", "work", "employment", "unemployment", "labour", "occupation", "worker"],
            "health": ["health", "medical", "hospital", "illness", "disease", "healthcare", "doctor"],
            "agriculture": ["farm", "agriculture", "crop", "cultivation", "livestock", "farmer"],
            "education": ["education", "school", "college", "study", "learning", "student", "teacher"],
            "household": ["household", "family", "income", "expenditure", "consumption", "home"]
        }
        self.audience_keywords = {
            "women": ["women", "female", "mother", "lady", "ladies"],
            "youth": ["youth", "young", "adolescent", "teenager"],
            "elderly": ["elderly", "senior", "old", "aged"],
            "children": ["children", "child", "kid"],
            "farmers": ["farmer", "cultivator", "agriculturist"]
        }
        self.location_keywords = {
            "rural": ["rural", "village", "countryside"],
            "urban": ["urban", "city", "town", "metropolitan"]
        }

    def parse(self, prompt: str) -> ParsedIntent:
        return ParsedIntent(
            domain=self._extract_domain(prompt),
            audience=self._extract_audience(prompt),
            location_type=self._extract_location(prompt),
            topics=self._extract_topics(prompt),
            num_questions=self._extract_number(prompt),
            special_requirements=self._extract_special(prompt),
            language=self._extract_language(prompt)
        )

    def _extract_domain(self, prompt: str) -> str:
        p = prompt.lower()
        for domain, kws in self.domain_keywords.items():
            if any(kw in p for kw in kws):
                return domain
        return "general"

    def _extract_audience(self, prompt: str) -> List[str]:
        p = prompt.lower()
        result = [a for a, kws in self.audience_keywords.items() if any(kw in p for kw in kws)]
        return result or ["general"]

    def _extract_location(self, prompt: str) -> Optional[str]:
        p = prompt.lower()
        for loc, kws in self.location_keywords.items():
            if any(kw in p for kw in kws):
                return loc
        return None

    def _extract_number(self, prompt: str) -> Optional[int]:
        m = re.search(r'(\d+)\s*(?:questions|items|queries)', prompt.lower())
        return int(m.group(1)) if m else None

    def _extract_topics(self, prompt: str) -> List[str]:
        stopwords = {"with", "about", "that", "this", "from", "have", "will",
                     "survey", "questions", "items", "for", "and", "the", "a", "an"}
        words = re.findall(r'\b[a-z]{4,}\b', prompt.lower())
        return [w for w in words if w not in stopwords][:5]

    def _extract_special(self, prompt: str) -> List[str]:
        p = prompt.lower()
        patterns = {
            "income": r"income|earning|salary|wage",
            "satisfaction": r"satisfaction|happy|rating",
            "multilingual": r"multilingual|hindi|regional|local language",
            "validation": r"validat|check|verify",
            "routing": r"routing|skip|logic|conditional"
        }
        return [req for req, pat in patterns.items() if re.search(pat, p)]

    def _extract_language(self, prompt: str) -> List[str]:
        p = prompt.lower()
        lang_map = {"hindi": "hi", "tamil": "ta", "bengali": "bn", "telugu": "te", "marathi": "mr"}
        langs = [code for name, code in lang_map.items() if name in p]
        if not langs:
            langs.append("en")
        elif "en" not in langs:
            langs.append("en")
        return langs
