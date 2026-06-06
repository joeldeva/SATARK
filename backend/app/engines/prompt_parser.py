"""Prompt parsing engine using NLP and rules (no LLM)."""

import re
import spacy
from typing import Dict, List, Optional, Tuple
from langdetect import detect
import logging

from ..models.prompt import PromptIntent

# Import config with proper path handling
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import MOSPI_DOMAINS, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


class PromptParser:
    """Parse user prompts to extract survey intent using NLP and rules."""
    
    def __init__(self):
        """Initialize the prompt parser."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Domain keywords mapping
        self.domain_keywords = {
            "labour": [
                "employment", "job", "work", "occupation", "career", "unemployment",
                "salary", "wage", "income", "employer", "employee", "labour", "labor"
            ],
            "health": [
                "health", "healthcare", "medical", "hospital", "doctor", "treatment",
                "disease", "illness", "medicine", "clinic", "vaccination", "nutrition"
            ],
            "education": [
                "education", "school", "college", "university", "student", "teacher",
                "learning", "literacy", "degree", "qualification", "training"
            ],
            "agriculture": [
                "agriculture", "farming", "crop", "farmer", "livestock", "irrigation",
                "harvest", "cultivation", "rural", "village", "land"
            ],
            "household": [
                "household", "family", "home", "domestic", "housing", "residence",
                "living", "dwelling", "amenities", "utilities"
            ],
            "enterprise": [
                "business", "enterprise", "company", "industry", "manufacturing",
                "trade", "commerce", "establishment", "firm", "organization"
            ]
        }
        
        # Audience keywords
        self.audience_keywords = {
            "women": ["women", "female", "lady", "mother", "wife"],
            "men": ["men", "male", "father", "husband"],
            "youth": ["youth", "young", "teenager", "adolescent"],
            "elderly": ["elderly", "old", "senior", "aged"],
            "rural": ["rural", "village", "countryside", "remote"],
            "urban": ["urban", "city", "metropolitan", "town"],
            "children": ["children", "child", "kid", "minor"],
            "students": ["student", "pupil", "learner"],
            "workers": ["worker", "employee", "staff", "laborer"]
        }
        
        # Language detection patterns
        self.language_patterns = {
            "hindi": ["hindi", "हिंदी", "devanagari"],
            "bengali": ["bengali", "bangla", "বাংলা"],
            "tamil": ["tamil", "தமிழ்"],
            "telugu": ["telugu", "తెలుగు"],
            "marathi": ["marathi", "मराठी"],
            "gujarati": ["gujarati", "ગુજરાતી"],
            "kannada": ["kannada", "ಕನ್ನಡ"],
            "malayalam": ["malayalam", "മലയാളം"],
            "odia": ["odia", "oriya", "ଓଡ଼ିଆ"]
        }
    
    def parse(self, prompt: str) -> PromptIntent:
        """Parse prompt and extract structured intent."""
        prompt_lower = prompt.lower().strip()
        
        # Extract components
        audience = self._extract_audience(prompt_lower)
        domain = self._extract_domain(prompt_lower)
        topic = self._extract_topic(prompt_lower)
        num_questions = self._extract_question_count(prompt_lower)
        keywords = self._extract_keywords(prompt_lower)
        languages = self._extract_languages(prompt_lower)
        special_requirements = self._extract_special_requirements(prompt_lower)
        
        return PromptIntent(
            audience=audience,
            domain=domain,
            topic=topic,
            num_questions=num_questions,
            keywords=keywords,
            language=languages,
            special_requirements=special_requirements
        )
    
    def _extract_audience(self, prompt: str) -> Optional[str]:
        """Extract target audience from prompt."""
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
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_domain(self, prompt: str) -> Optional[str]:
        """Extract survey domain from prompt."""
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in prompt)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def _extract_topic(self, prompt: str) -> Optional[str]:
        """Extract main topic from prompt."""
        # Look for "about X" patterns
        about_patterns = [
            r"about ([a-zA-Z\s]+)",
            r"regarding ([a-zA-Z\s]+)",
            r"on ([a-zA-Z\s]+)",
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, prompt)
            if match:
                topic = match.group(1).strip()
                # Clean up common stop words
                topic = re.sub(r'\b(with|and|or|the|a|an)\b', '', topic).strip()
                if topic:
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
        # Look for number patterns
        patterns = [
            r"(\d+)\s+questions?",
            r"with\s+(\d+)\s+questions?",
            r"(\d+)\s+items?",
            r"around\s+(\d+)",
            r"about\s+(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                count = int(match.group(1))
                if 3 <= count <= 50:  # Reasonable range
                    return count
        
        return None
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract important keywords from prompt."""
        keywords = []
        
        if self.nlp:
            doc = self.nlp(prompt)
            # Extract nouns, adjectives, and proper nouns
            for token in doc:
                if (token.pos_ in ["NOUN", "ADJ", "PROPN"] and 
                    len(token.text) > 2 and 
                    not token.is_stop and 
                    not token.is_punct):
                    keywords.append(token.lemma_.lower())
        else:
            # Fallback: simple word extraction
            words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt)
            keywords = [w.lower() for w in words if w.lower() not in 
                       ["the", "and", "for", "with", "about", "survey", "questions"]]
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_languages(self, prompt: str) -> List[str]:
        """Extract requested languages from prompt."""
        languages = ["en"]  # Default to English
        
        for lang_name, patterns in self.language_patterns.items():
            for pattern in patterns:
                if pattern in prompt:
                    lang_code = self._get_language_code(lang_name)
                    if lang_code and lang_code not in languages:
                        languages.append(lang_code)
        
        # Look for explicit language mentions
        if "bilingual" in prompt or "multilingual" in prompt:
            languages.append("hi")  # Add Hindi as common second language
        
        return languages
    
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
            "odia": "or"
        }
        return mapping.get(language_name)
    
    def _extract_special_requirements(self, prompt: str) -> List[str]:
        """Extract special requirements or constraints."""
        requirements = []
        
        # Common requirement patterns
        requirement_patterns = {
            "include income": r"includ\w*\s+income",
            "include satisfaction": r"includ\w*\s+satisfaction",
            "skip logic": r"skip\s+logic|conditional|routing",
            "validation": r"validat\w+|check\w+|verif\w+",
            "mobile friendly": r"mobile|phone|whatsapp",
            "short survey": r"short|brief|quick",
            "detailed survey": r"detailed|comprehensive|thorough",
            "anonymous": r"anonymous|confidential|private"
        }
        
        for requirement, pattern in requirement_patterns.items():
            if re.search(pattern, prompt):
                requirements.append(requirement)
        
        return requirements