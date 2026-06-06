"""
SATARK.AI Prompt Parser
NLP + Rules-based intent extraction (No LLM)
"""

import re
import spacy
from typing import Dict, List, Optional, Tuple
from langdetect import detect
import logging

from models.survey_schema import PromptIntent
from config import MOSPI_DOMAINS, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


class PromptParser:
    """
    Deterministic prompt parsing using NLP + Rules.
    No LLM dependency - fully explainable and auditable.
    """
    
    def __init__(self):
        """Initialize the prompt parser."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy model loaded successfully")
        except OSError:
            logger.warning("⚠️ spaCy model not found, using fallback parsing")
            self.nlp = None
        
        # Domain keyword mappings (deterministic classification)
        self.domain_keywords = {
            "labour": [
                "employment", "job", "work", "occupation", "career", "unemployment",
                "salary", "wage", "income", "employer", "employee", "labour", "labor",
                "workforce", "employment status", "job satisfaction", "working hours"
            ],
            "health": [
                "health", "healthcare", "medical", "hospital", "doctor", "treatment",
                "disease", "illness", "medicine", "clinic", "vaccination", "nutrition",
                "maternal", "child health", "mortality", "morbidity", "insurance"
            ],
            "education": [
                "education", "school", "college", "university", "student", "teacher",
                "learning", "literacy", "degree", "qualification", "training",
                "enrollment", "dropout", "academic", "curriculum"
            ],
            "agriculture": [
                "agriculture", "farming", "crop", "farmer", "livestock", "irrigation",
                "harvest", "cultivation", "rural", "village", "land", "agricultural",
                "farming practices", "crop yield", "animal husbandry"
            ],
            "household": [
                "household", "family", "home", "domestic", "housing", "residence",
                "living", "dwelling", "amenities", "utilities", "consumption",
                "expenditure", "assets", "living standards"
            ],
            "enterprise": [
                "business", "enterprise", "company", "industry", "manufacturing",
                "trade", "commerce", "establishment", "firm", "organization",
                "startup", "msme", "industrial", "commercial"
            ],
            "social": [
                "social", "community", "society", "cultural", "caste", "religion",
                "social group", "discrimination", "inclusion", "welfare"
            ],
            "economic": [
                "economic", "economy", "financial", "poverty", "wealth", "gdp",
                "economic indicators", "financial inclusion", "banking"
            ],
            "demographic": [
                "demographic", "population", "census", "age", "gender", "migration",
                "birth rate", "death rate", "population growth"
            ]
        }
        
        # Audience keyword mappings
        self.audience_keywords = {
            "women": ["women", "female", "lady", "mother", "wife", "girl"],
            "men": ["men", "male", "father", "husband", "boy"],
            "youth": ["youth", "young", "teenager", "adolescent"],
            "elderly": ["elderly", "old", "senior", "aged"],
            "rural": ["rural", "village", "countryside", "remote", "gram"],
            "urban": ["urban", "city", "metropolitan", "town", "municipal"],
            "children": ["children", "child", "kid", "minor", "infant"],
            "students": ["student", "pupil", "learner", "scholar"],
            "workers": ["worker", "employee", "staff", "laborer", "labour"],
            "farmers": ["farmer", "cultivator", "agriculturist"],
            "entrepreneurs": ["entrepreneur", "business owner", "msme owner"]
        }
        
        # Language detection patterns
        self.language_patterns = {
            "hindi": ["hindi", "हिंदी", "devanagari", "हिन्दी"],
            "bengali": ["bengali", "bangla", "বাংলা"],
            "tamil": ["tamil", "தமிழ்"],
            "telugu": ["telugu", "తెలుగు"],
            "marathi": ["marathi", "मराठी"],
            "gujarati": ["gujarati", "ગુજરાતી"],
            "kannada": ["kannada", "ಕನ್ನಡ"],
            "malayalam": ["malayalam", "മലയാളം"],
            "odia": ["odia", "oriya", "ଓଡ଼ିଆ"],
            "punjabi": ["punjabi", "ਪੰਜਾਬੀ"],
            "assamese": ["assamese", "অসমীয়া"],
            "urdu": ["urdu", "اردو"]
        }
        
        # Special requirement patterns
        self.requirement_patterns = {
            "income_questions": r"includ\w*\s+(income|salary|wage|earning)",
            "satisfaction": r"satisfaction|happy|content",
            "skip_logic": r"skip\s+logic|conditional|routing",
            "validation": r"validat\w+|check\w+|verif\w+",
            "mobile_friendly": r"mobile|phone|whatsapp|app",
            "short_survey": r"short|brief|quick|fast",
            "detailed_survey": r"detailed|comprehensive|thorough|extensive",
            "anonymous": r"anonymous|confidential|private",
            "multilingual": r"multilingual|bilingual|multiple\s+language"
        }
    
    def parse(self, prompt: str) -> PromptIntent:
        """
        Parse prompt and extract structured intent.
        Uses deterministic NLP + Rules approach.
        """
        prompt_lower = prompt.lower().strip()
        
        logger.info(f"🔍 Parsing prompt: {prompt[:50]}...")
        
        # Extract components using deterministic methods
        domain = self._extract_domain(prompt_lower)
        audience = self._extract_audience(prompt_lower)
        topic = self._extract_topic(prompt_lower)
        num_questions = self._extract_question_count(prompt_lower)
        keywords = self._extract_keywords(prompt_lower)
        languages = self._extract_languages(prompt_lower)
        requirements = self._extract_requirements(prompt_lower)
        
        # Calculate confidence based on keyword matches
        confidence = self._calculate_confidence(prompt_lower, domain)
        
        intent = PromptIntent(
            domain=domain,
            audience=audience,
            topic=topic,
            num_questions=num_questions,
            keywords=keywords,
            languages=languages,
            requirements=requirements,
            confidence=confidence
        )
        
        logger.info(f"✅ Intent extracted: domain={domain}, audience={audience}, confidence={confidence:.2f}")
        
        return intent
    
    def _extract_domain(self, prompt: str) -> Optional[str]:
        """Extract survey domain using keyword matching."""
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in prompt)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            logger.debug(f"Domain scores: {domain_scores}, selected: {best_domain}")
            return best_domain
        
        return None
    
    def _extract_audience(self, prompt: str) -> Optional[str]:
        """Extract target audience using keyword matching."""
        audience_parts = []
        
        for audience_type, keywords in self.audience_keywords.items():
            for keyword in keywords:
                if keyword in prompt:
                    audience_parts.append(audience_type)
                    break
        
        if audience_parts:
            return " ".join(audience_parts)
        
        # Try to extract custom audience using patterns
        patterns = [
            r"for ([a-zA-Z\s]+) about",
            r"survey for ([a-zA-Z\s]+)",
            r"targeting ([a-zA-Z\s]+)",
            r"among ([a-zA-Z\s]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_topic(self, prompt: str) -> Optional[str]:
        """Extract main topic using pattern matching."""
        # Look for "about X" patterns
        about_patterns = [
            r"about ([a-zA-Z\s]+)",
            r"regarding ([a-zA-Z\s]+)",
            r"on ([a-zA-Z\s]+)",
            r"related to ([a-zA-Z\s]+)"
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, prompt)
            if match:
                topic = match.group(1).strip()
                # Clean up common stop words
                topic = re.sub(r'\b(with|and|or|the|a|an|in|of|to|for)\b', '', topic).strip()
                if topic and len(topic) > 2:
                    return topic
        
        # Extract using spaCy if available
        if self.nlp:
            doc = self.nlp(prompt)
            # Look for noun phrases that might be topics
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3 and chunk.root.pos_ == "NOUN":
                    return chunk.text
        
        return None
    
    def _extract_question_count(self, prompt: str) -> Optional[int]:
        """Extract requested number of questions."""
        patterns = [
            r"(\d+)\s+questions?",
            r"with\s+(\d+)\s+questions?",
            r"(\d+)\s+items?",
            r"around\s+(\d+)",
            r"about\s+(\d+)",
            r"approximately\s+(\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                count = int(match.group(1))
                if 3 <= count <= 50:  # Reasonable range
                    return count
        
        return None
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract important keywords using NLP."""
        keywords = []
        
        if self.nlp:
            doc = self.nlp(prompt)
            # Extract nouns, adjectives, and proper nouns
            for token in doc:
                if (token.pos_ in ["NOUN", "ADJ", "PROPN"] and 
                    len(token.text) > 2 and 
                    not token.is_stop and 
                    not token.is_punct and
                    token.text.isalpha()):
                    keywords.append(token.lemma_.lower())
        else:
            # Fallback: simple word extraction
            words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt)
            stop_words = {"the", "and", "for", "with", "about", "survey", "questions", "question"}
            keywords = [w.lower() for w in words if w.lower() not in stop_words]
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_languages(self, prompt: str) -> List[str]:
        """Extract requested languages."""
        languages = ["en"]  # Default to English
        
        for lang_name, patterns in self.language_patterns.items():
            for pattern in patterns:
                if pattern in prompt:
                    lang_code = self._get_language_code(lang_name)
                    if lang_code and lang_code not in languages:
                        languages.append(lang_code)
        
        # Look for explicit language mentions
        if "bilingual" in prompt or "multilingual" in prompt:
            if "hi" not in languages:
                languages.append("hi")  # Add Hindi as common second language
        
        return languages
    
    def _extract_requirements(self, prompt: str) -> List[str]:
        """Extract special requirements."""
        requirements = []
        
        for requirement, pattern in self.requirement_patterns.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                requirements.append(requirement)
        
        return requirements
    
    def _calculate_confidence(self, prompt: str, domain: Optional[str]) -> float:
        """Calculate confidence score based on keyword matches."""
        if not domain:
            return 0.0
        
        domain_keywords = self.domain_keywords.get(domain, [])
        matches = sum(1 for keyword in domain_keywords if keyword in prompt)
        
        # Base confidence on keyword density
        confidence = min(matches / len(domain_keywords) * 2, 1.0)
        
        # Boost confidence for explicit domain mentions
        if domain in prompt:
            confidence = min(confidence + 0.3, 1.0)
        
        return round(confidence, 2)
    
    def _get_language_code(self, language_name: str) -> Optional[str]:
        """Convert language name to ISO code."""
        mapping = {
            "hindi": "hi",
            "bengali": "bn", 
            "tamil": "ta",
            "telugu": "te",
            "marathi": "mr",
            "gujarati": "gu",
            "kannada": "kn",
            "malayalam": "ml",
            "odia": "or",
            "punjabi": "pa",
            "assamese": "as",
            "urdu": "ur"
        }
        return mapping.get(language_name)