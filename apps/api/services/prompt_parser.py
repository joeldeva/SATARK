import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParsedIntent:
    domain: str
    audience: List[str]
    location_type: Optional[str]
    topics: List[str]
    num_questions: Optional[int]
    special_requirements: List[str]
    language: List[str] = field(default_factory=lambda: ["en"])
    planner: str = "deterministic"
    planner_model: Optional[str] = None
    planner_confidence: Optional[int] = None
    planner_reason: Optional[str] = None
    assist_framework: Optional[str] = None
    draft_questions: List[Dict] = field(default_factory=list)


class PromptParser:
    """Deterministic prompt parser with no external model dependency."""

    def __init__(self):
        self.domain_keywords = {
            "labour": ["job", "work", "employment", "unemployment", "labour", "labor", "occupation", "worker", "salary", "wage"],
            "health": ["health", "medical", "hospital", "illness", "disease", "healthcare", "doctor", "insurance"],
            "agriculture": ["farm", "agriculture", "crop", "cultivation", "livestock", "farmer", "irrigation", "land"],
            "education": ["education", "school", "college", "study", "learning", "student", "teacher", "literacy"],
            "household": ["household", "family", "income", "expenditure", "consumption", "home", "housing", "water"],
            "enterprise": ["business", "enterprise", "msme", "industry", "manufacturing", "trade", "turnover"],
            "social": ["welfare", "scheme", "community", "ration", "bank", "beneficiary"],
        }
        self.audience_keywords = {
            "women": ["women", "female", "mother", "lady", "ladies"],
            "men": ["men", "male", "father"],
            "youth": ["youth", "young", "adolescent", "teenager"],
            "elderly": ["elderly", "senior", "old", "aged"],
            "children": ["children", "child", "kid"],
            "farmers": ["farmer", "cultivator", "agriculturist"],
            "workers": ["worker", "employee", "labourer", "laborer"],
            "entrepreneurs": ["entrepreneur", "business owner", "msme owner"],
        }
        self.location_keywords = {
            "rural": ["rural", "village", "countryside"],
            "urban": ["urban", "city", "town", "metropolitan"],
        }

    def parse(self, prompt: str) -> ParsedIntent:
        return ParsedIntent(
            domain=self._extract_domain(prompt),
            audience=self._extract_audience(prompt),
            location_type=self._extract_location(prompt),
            topics=self._extract_topics(prompt),
            num_questions=self._extract_number(prompt),
            special_requirements=self._extract_special(prompt),
            language=self._extract_language(prompt),
        )

    def _extract_domain(self, prompt: str) -> str:
        p = prompt.lower()
        scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in p)
            if score:
                scores[domain] = score
        return max(scores, key=scores.get) if scores else "household"

    def _extract_audience(self, prompt: str) -> List[str]:
        p = prompt.lower()
        result = [audience for audience, keywords in self.audience_keywords.items() if any(keyword in p for keyword in keywords)]
        return result or ["general"]

    def _extract_location(self, prompt: str) -> Optional[str]:
        p = prompt.lower()
        for location, keywords in self.location_keywords.items():
            if any(keyword in p for keyword in keywords):
                return location
        return None

    def _extract_number(self, prompt: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*(?:questions|items|queries)", prompt.lower())
        if not match:
            return None
        return max(3, min(int(match.group(1)), 50))

    def _extract_topics(self, prompt: str) -> List[str]:
        stopwords = {
            "with", "about", "that", "this", "from", "have", "will", "survey",
            "questions", "items", "queries", "for", "and", "the", "are", "their",
        }
        words = re.findall(r"\b[a-z]{4,}\b", prompt.lower())
        topics = []
        for word in words:
            if word not in stopwords and word not in topics:
                topics.append(word)
        return topics[:8]

    def _extract_special(self, prompt: str) -> List[str]:
        p = prompt.lower()
        patterns = {
            "income": r"income|earning|salary|wage",
            "satisfaction": r"satisfaction|happy|rating",
            "multilingual": r"multilingual|hindi|regional|local language",
            "validation": r"validat|check|verify",
            "routing": r"routing|skip|logic|conditional",
        }
        return [name for name, pattern in patterns.items() if re.search(pattern, p)]

    def _extract_language(self, prompt: str) -> List[str]:
        p = prompt.lower()
        lang_map = {
            "english": "en", "hindi": "hi", "हिन्दी": "hi", "tamil": "ta", "தமிழ்": "ta",
            "telugu": "te", "తెలుగు": "te", "kannada": "kn", "ಕನ್ನಡ": "kn",
            "malayalam": "ml", "മലയാളം": "ml", "bengali": "bn", "bangla": "bn", "বাংলা": "bn",
            "gujarati": "gu", "ગુજરાતી": "gu", "punjabi": "pa", "ਪੰਜਾਬੀ": "pa",
            "assamese": "as", "অসমীয়া": "as", "odia": "or", "oriya": "or", "ଓଡ଼ିଆ": "or",
            "marathi": "mr", "मराठी": "mr", "urdu": "ur", "اردو": "ur",
            "konkani": "kok", "sanskrit": "sa", "manipuri": "mni", "bodo": "brx",
            "dogri": "doi", "maithili": "mai", "nepali": "ne", "santali": "sat", "kashmiri": "ks",
        }
        languages = ["en"]
        for name, code in lang_map.items():
            if name in p and code not in languages:
                languages.append(code)
        return languages
