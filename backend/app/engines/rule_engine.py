"""Rule-based survey generation engine for deterministic logic."""

from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from ..models.survey import (
    Question, QuestionType, QuestionCategory, MultilingualText,
    AnswerOption, ValidationRule, SurveyDomain, Survey, SurveyMetadata,
    SurveyStandard
)
from ..models.prompt import PromptIntent

# Import config with proper path handling
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import MANDATORY_DEMOGRAPHICS, VALIDATION_RULES, QUESTION_CATEGORIES

logger = logging.getLogger(__name__)


class RuleEngine:
    """Rule-based survey generation engine."""
    
    def __init__(self):
        """Initialize the rule engine."""
        self.demographic_templates = self._load_demographic_templates()
        self.validation_rules = VALIDATION_RULES
        self.question_counter = 0
    
    def generate_mandatory_questions(self, intent: PromptIntent) -> List[Question]:
        """Generate mandatory demographic questions based on domain."""
        questions = []
        self.question_counter = 0
        
        # Always include basic demographics
        for demo_type in MANDATORY_DEMOGRAPHICS:
            if demo_type in self.demographic_templates:
                question = self._create_demographic_question(demo_type, intent.language)
                questions.append(question)
        
        return questions
    
    def apply_domain_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply domain-specific rules to questions."""
        domain = intent.domain
        
        if domain == "labour":
            questions = self._apply_labour_rules(questions, intent)
        elif domain == "health":
            questions = self._apply_health_rules(questions, intent)
        elif domain == "education":
            questions = self._apply_education_rules(questions, intent)
        elif domain == "agriculture":
            questions = self._apply_agriculture_rules(questions, intent)
        elif domain == "household":
            questions = self._apply_household_rules(questions, intent)
        elif domain == "enterprise":
            questions = self._apply_enterprise_rules(questions, intent)
        
        return questions
    
    def add_validation_rules(self, questions: List[Question]) -> List[Question]:
        """Add appropriate validation rules to questions."""
        for question in questions:
            if question.type == QuestionType.NUMBER:
                question.validation = self._get_number_validation(question.id)
            elif question.type == QuestionType.TEXT:
                question.validation = self._get_text_validation(question.id)
        
        return questions
    
    def order_questions(self, questions: List[Question]) -> List[Question]:
        """Order questions according to best practices."""
        # Sort by category priority
        category_order = {
            QuestionCategory.DEMOGRAPHIC: 1,
            QuestionCategory.CORE: 2,
            QuestionCategory.SENSITIVE: 3,
            QuestionCategory.FOLLOW_UP: 4
        }
        
        return sorted(questions, key=lambda q: category_order.get(q.category, 5))
    
    def create_survey_metadata(self, intent: PromptIntent) -> SurveyMetadata:
        """Create survey metadata based on intent."""
        # Determine standard based on domain
        standard_mapping = {
            "labour": SurveyStandard.PLFS,
            "health": SurveyStandard.NFHS,
            "household": SurveyStandard.NSS,
            "enterprise": SurveyStandard.ASI
        }
        
        standard = standard_mapping.get(intent.domain, SurveyStandard.CUSTOM)
        
        return SurveyMetadata(
            standard=standard,
            created_by="AI_Rule_Engine",
            version="1.0",
            gsbpm_phase="design",
            deployment_channels=["web", "mobile_app"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    def _load_demographic_templates(self) -> Dict[str, Dict]:
        """Load demographic question templates."""
        return {
            "age": {
                "text": {
                    "en": "What is your age?",
                    "hi": "आपकी उम्र क्या है?"
                },
                "type": QuestionType.NUMBER,
                "validation": {"min": 0, "max": 120},
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_AGE"
            },
            "gender": {
                "text": {
                    "en": "What is your gender?",
                    "hi": "आपका लिंग क्या है?"
                },
                "type": QuestionType.SINGLE_CHOICE,
                "options": [
                    {"value": "1", "label": {"en": "Male", "hi": "पुरुष"}},
                    {"value": "2", "label": {"en": "Female", "hi": "महिला"}},
                    {"value": "3", "label": {"en": "Other", "hi": "अन्य"}}
                ],
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_GENDER"
            },
            "location": {
                "text": {
                    "en": "What is your location type?",
                    "hi": "आपके स्थान का प्रकार क्या है?"
                },
                "type": QuestionType.SINGLE_CHOICE,
                "options": [
                    {"value": "1", "label": {"en": "Rural", "hi": "ग्रामीण"}},
                    {"value": "2", "label": {"en": "Urban", "hi": "शहरी"}}
                ],
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_LOCATION"
            }
        }
    
    def _create_demographic_question(self, demo_type: str, languages: List[str]) -> Question:
        """Create a demographic question from template."""
        template = self.demographic_templates[demo_type]
        self.question_counter += 1
        
        # Create multilingual text
        text_dict = {}
        for lang in languages:
            if lang in template["text"]:
                text_dict[lang] = template["text"][lang]
            elif lang == "en":
                text_dict[lang] = template["text"]["en"]
        
        text = MultilingualText(**text_dict)
        
        # Create options if needed
        options = None
        if "options" in template:
            options = []
            for opt in template["options"]:
                label_dict = {}
                for lang in languages:
                    if lang in opt["label"]:
                        label_dict[lang] = opt["label"][lang]
                    elif lang == "en":
                        label_dict[lang] = opt["label"]["en"]
                
                options.append(AnswerOption(
                    value=opt["value"],
                    label=MultilingualText(**label_dict)
                ))
        
        # Create validation
        validation = None
        if "validation" in template:
            validation = ValidationRule(**template["validation"])
        
        return Question(
            id=f"Q{self.question_counter}",
            text=text,
            type=template["type"],
            required=True,
            options=options,
            validation=validation,
            category=template["category"],
            standard_code=template.get("standard_code")
        )
    
    def _apply_labour_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply labour domain specific rules."""
        # Add employment status question
        self.question_counter += 1
        employment_q = Question(
            id=f"Q{self.question_counter}",
            text=MultilingualText(
                en="What is your current employment status?",
                hi="आपकी वर्तमान रोजगार स्थिति क्या है?"
            ),
            type=QuestionType.SINGLE_CHOICE,
            required=True,
            options=[
                AnswerOption(value="1", label=MultilingualText(en="Employed", hi="नियोजित")),
                AnswerOption(value="2", label=MultilingualText(en="Unemployed", hi="बेरोजगार")),
                AnswerOption(value="3", label=MultilingualText(en="Self-employed", hi="स्व-नियोजित")),
                AnswerOption(value="4", label=MultilingualText(en="Student", hi="छात्र")),
                AnswerOption(value="5", label=MultilingualText(en="Retired", hi="सेवानिवृत्त"))
            ],
            category=QuestionCategory.CORE,
            standard_code="LAB_EMP_STATUS"
        )
        questions.append(employment_q)
        
        return questions
    
    def _apply_health_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply health domain specific rules."""
        # Add health status question
        self.question_counter += 1
        health_q = Question(
            id=f"Q{self.question_counter}",
            text=MultilingualText(
                en="How would you rate your overall health?",
                hi="आप अपने समग्र स्वास्थ्य को कैसे दर्जा देंगे?"
            ),
            type=QuestionType.SINGLE_CHOICE,
            required=True,
            options=[
                AnswerOption(value="1", label=MultilingualText(en="Excellent", hi="उत्कृष्ट")),
                AnswerOption(value="2", label=MultilingualText(en="Good", hi="अच्छा")),
                AnswerOption(value="3", label=MultilingualText(en="Fair", hi="ठीक")),
                AnswerOption(value="4", label=MultilingualText(en="Poor", hi="खराब"))
            ],
            category=QuestionCategory.CORE,
            standard_code="HEALTH_STATUS"
        )
        questions.append(health_q)
        
        return questions
    
    def _apply_education_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply education domain specific rules."""
        return questions
    
    def _apply_agriculture_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply agriculture domain specific rules."""
        return questions
    
    def _apply_household_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply household domain specific rules."""
        return questions
    
    def _apply_enterprise_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply enterprise domain specific rules."""
        return questions
    
    def _get_number_validation(self, question_id: str) -> Optional[ValidationRule]:
        """Get validation rules for number questions."""
        # Map question IDs to validation rules
        if "age" in question_id.lower():
            return ValidationRule(min=0, max=120)
        elif "income" in question_id.lower():
            return ValidationRule(min=0, max=10000000)
        elif "experience" in question_id.lower():
            return ValidationRule(min=0, max=60)
        
        return ValidationRule(min=0)  # Default: non-negative
    
    def _get_text_validation(self, question_id: str) -> Optional[ValidationRule]:
        """Get validation rules for text questions."""
        # Basic text validation
        return ValidationRule(pattern=r"^.{1,500}$")  # Max 500 characters