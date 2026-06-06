"""
SATARK.AI Survey Builder
Deterministic survey construction using rules
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime
import logging

from models.survey_schema import (
    Survey, Question, QuestionType, QuestionCategory, MultilingualText,
    AnswerOption, ValidationRule, RoutingRule, SurveyDomain, SurveyMetadata,
    PromptIntent, Language
)
from config import MANDATORY_DEMOGRAPHICS, QUESTION_CATEGORIES

logger = logging.getLogger(__name__)


class SurveyBuilder:
    """
    Deterministic survey builder using rule-based logic.
    No randomness - fully predictable and auditable.
    """
    
    def __init__(self):
        """Initialize the survey builder."""
        self.question_counter = 0
        
        # Standard demographic questions
        self.demographic_templates = {
            "age": {
                "text": {"en": "What is your age?", "hi": "आपकी उम्र क्या है?"},
                "type": QuestionType.NUMBER,
                "validation": {"min_value": 0, "max_value": 120, "required": True},
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_AGE"
            },
            "gender": {
                "text": {"en": "What is your gender?", "hi": "आपका लिंग क्या है?"},
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
                "text": {"en": "What is your location type?", "hi": "आपके स्थान का प्रकार क्या है?"},
                "type": QuestionType.SINGLE_CHOICE,
                "options": [
                    {"value": "1", "label": {"en": "Rural", "hi": "ग्रामीण"}},
                    {"value": "2", "label": {"en": "Urban", "hi": "शहरी"}}
                ],
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_LOCATION"
            },
            "education": {
                "text": {"en": "What is your highest level of education?", "hi": "आपकी उच्चतम शिक्षा का स्तर क्या है?"},
                "type": QuestionType.SINGLE_CHOICE,
                "options": [
                    {"value": "1", "label": {"en": "No formal education", "hi": "कोई औपचारिक शिक्षा नहीं"}},
                    {"value": "2", "label": {"en": "Primary", "hi": "प्राथमिक"}},
                    {"value": "3", "label": {"en": "Secondary", "hi": "माध्यमिक"}},
                    {"value": "4", "label": {"en": "Higher Secondary", "hi": "उच्च माध्यमिक"}},
                    {"value": "5", "label": {"en": "Graduate", "hi": "स्नातक"}},
                    {"value": "6", "label": {"en": "Post Graduate", "hi": "स्नातकोत्तर"}}
                ],
                "category": QuestionCategory.DEMOGRAPHIC,
                "standard_code": "DEMO_EDUCATION"
            }
        }
    
    def build_survey(self, intent: PromptIntent, retrieved_questions: List[Dict], max_questions: int) -> Survey:
        """
        Build complete survey using deterministic rules.
        
        Process:
        1. Add mandatory demographic questions
        2. Convert retrieved questions to Question objects
        3. Apply domain-specific rules
        4. Order questions logically
        5. Add validation and routing
        6. Create survey metadata
        """
        logger.info(f"🏗️ Building survey for domain: {intent.domain}")
        
        # Reset counter
        self.question_counter = 0
        
        # Step 1: Add mandatory demographic questions
        questions = self._add_demographic_questions(intent.languages)
        
        # Step 2: Convert and add retrieved questions
        domain_questions = self._convert_retrieved_questions(retrieved_questions, intent.languages)
        questions.extend(domain_questions)
        
        # Step 3: Apply domain-specific rules
        questions = self._apply_domain_rules(questions, intent)
        
        # Step 4: Remove duplicates and limit count
        questions = self._deduplicate_questions(questions)
        if len(questions) > max_questions:
            questions = self._select_best_questions(questions, max_questions)
        
        # Step 5: Order questions logically
        questions = self._order_questions(questions)
        
        # Step 6: Add routing logic
        questions = self._add_routing_logic(questions)
        
        # Step 7: Create survey metadata
        metadata = self._create_metadata(intent)
        
        # Step 8: Generate title
        title = self._generate_title(intent)
        
        # Step 9: Determine domain
        domain = self._determine_domain(intent)
        
        # Step 10: Set languages
        languages = [Language(lang) for lang in intent.languages if lang in [l.value for l in Language]]
        if not languages:
            languages = [Language.ENGLISH]
        
        # Create survey
        survey = Survey(
            survey_id=str(uuid.uuid4()),
            title=title,
            domain=domain,
            target_audience=intent.audience,
            languages=languages,
            questions=questions,
            metadata=metadata
        )
        
        logger.info(f"✅ Survey built with {len(questions)} questions")
        return survey
    
    def _add_demographic_questions(self, languages: List[str]) -> List[Question]:
        """Add mandatory demographic questions."""
        questions = []
        
        for demo_type in MANDATORY_DEMOGRAPHICS:
            if demo_type in self.demographic_templates:
                question = self._create_demographic_question(demo_type, languages)
                questions.append(question)
        
        logger.debug(f"Added {len(questions)} demographic questions")
        return questions
    
    def _create_demographic_question(self, demo_type: str, languages: List[str]) -> Question:
        """Create demographic question from template."""
        template = self.demographic_templates[demo_type]
        self.question_counter += 1
        
        # Create multilingual text
        text_dict = {}
        for lang in languages:
            if lang in template["text"]:
                text_dict[lang] = template["text"][lang]
            else:
                text_dict[lang] = template["text"]["en"]  # Fallback to English
        
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
                    else:
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
            id=f"Q{self.question_counter:03d}",
            text=text,
            type=template["type"],
            category=template["category"],
            required=True,
            options=options,
            validation=validation,
            standard_code=template.get("standard_code"),
            tags=["demographic", demo_type],
            source="SATARK.AI"
        )
    
    def _convert_retrieved_questions(self, retrieved_questions: List[Dict], languages: List[str]) -> List[Question]:
        """Convert retrieved question dictionaries to Question objects."""
        questions = []
        
        for q_data in retrieved_questions:
            try:
                question = self._convert_question_data(q_data, languages)
                if question:
                    questions.append(question)
            except Exception as e:
                logger.error(f"Error converting question {q_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.debug(f"Converted {len(questions)} retrieved questions")
        return questions
    
    def _convert_question_data(self, q_data: Dict, languages: List[str]) -> Optional[Question]:
        """Convert question data to Question object."""
        self.question_counter += 1
        
        # Create multilingual text
        question_text = q_data.get('text', {})
        if isinstance(question_text, str):
            question_text = {'en': question_text}
        
        text_dict = {}
        for lang in languages:
            if lang in question_text:
                text_dict[lang] = question_text[lang]
            else:
                text_dict[lang] = question_text.get('en', 'Question text not available')
        
        text = MultilingualText(**text_dict)
        
        # Map question type
        q_type = self._map_question_type(q_data.get('type', 'text'))
        
        # Create options if needed
        options = None
        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            options = self._create_options(q_data.get('options', []), languages)
        
        # Create validation
        validation = None
        if 'validation' in q_data:
            val_data = q_data['validation']
            validation = ValidationRule(
                min_value=val_data.get('min_value'),
                max_value=val_data.get('max_value'),
                pattern=val_data.get('pattern'),
                required=val_data.get('required', True),
                custom_rule=val_data.get('custom_rule')
            )
        
        # Create routing
        routing = None
        if 'routing' in q_data:
            routing_data = q_data['routing']
            routing = RoutingRule(
                condition=routing_data.get('condition'),
                skip_to=routing_data.get('skip_to'),
                show_if=routing_data.get('show_if')
            )
        
        # Map category
        category = self._map_question_category(q_data.get('category', 'core'))
        
        return Question(
            id=f"Q{self.question_counter:03d}",
            text=text,
            type=q_type,
            category=category,
            required=q_data.get('validation', {}).get('required', True),
            options=options,
            validation=validation,
            routing=routing,
            standard_code=q_data.get('standard_code'),
            tags=q_data.get('tags', []),
            source=q_data.get('source', 'Retrieved')
        )
    
    def _map_question_type(self, type_str: str) -> QuestionType:
        """Map string type to QuestionType enum."""
        mapping = {
            'single_choice': QuestionType.SINGLE_CHOICE,
            'multiple_choice': QuestionType.MULTIPLE_CHOICE,
            'number': QuestionType.NUMBER,
            'text': QuestionType.TEXT,
            'date': QuestionType.DATE,
            'scale': QuestionType.SCALE,
            'matrix': QuestionType.MATRIX,
            'boolean': QuestionType.BOOLEAN
        }
        return mapping.get(type_str, QuestionType.TEXT)
    
    def _map_question_category(self, category_str: str) -> QuestionCategory:
        """Map string category to QuestionCategory enum."""
        mapping = {
            'demographic': QuestionCategory.DEMOGRAPHIC,
            'core': QuestionCategory.CORE,
            'economic': QuestionCategory.ECONOMIC,
            'social': QuestionCategory.SOCIAL,
            'follow_up': QuestionCategory.FOLLOW_UP
        }
        return mapping.get(category_str, QuestionCategory.CORE)
    
    def _create_options(self, options_data: List[Dict], languages: List[str]) -> List[AnswerOption]:
        """Create AnswerOption objects from data."""
        options = []
        
        for opt_data in options_data:
            label_data = opt_data.get('label', {})
            if isinstance(label_data, str):
                label_data = {'en': label_data}
            
            label_dict = {}
            for lang in languages:
                if lang in label_data:
                    label_dict[lang] = label_data[lang]
                else:
                    label_dict[lang] = label_data.get('en', opt_data.get('value', ''))
            
            option = AnswerOption(
                value=opt_data.get('value', ''),
                label=MultilingualText(**label_dict),
                standard_code=opt_data.get('standard_code')
            )
            options.append(option)
        
        return options
    
    def _apply_domain_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply domain-specific rules."""
        domain = intent.domain
        
        if domain == "labour":
            questions = self._apply_labour_rules(questions, intent)
        elif domain == "health":
            questions = self._apply_health_rules(questions, intent)
        elif domain == "agriculture":
            questions = self._apply_agriculture_rules(questions, intent)
        
        return questions
    
    def _apply_labour_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply labour domain rules."""
        # Ensure employment status question comes first after demographics
        employment_questions = [q for q in questions if "employment" in q.tags]
        if employment_questions:
            # Move employment status to front of core questions
            for q in employment_questions:
                if q.category == QuestionCategory.CORE:
                    questions.remove(q)
                    questions.insert(len([q for q in questions if q.category == QuestionCategory.DEMOGRAPHIC]), q)
                    break
        
        return questions
    
    def _apply_health_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply health domain rules."""
        # Ensure health access questions come before satisfaction
        return questions
    
    def _apply_agriculture_rules(self, questions: List[Question], intent: PromptIntent) -> List[Question]:
        """Apply agriculture domain rules."""
        # Ensure land ownership questions come first
        return questions
    
    def _deduplicate_questions(self, questions: List[Question]) -> List[Question]:
        """Remove duplicate questions."""
        seen_texts = set()
        unique_questions = []
        
        for question in questions:
            text_key = question.text.en.lower().strip()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_questions.append(question)
        
        return unique_questions
    
    def _select_best_questions(self, questions: List[Question], max_questions: int) -> List[Question]:
        """Select best questions when over limit."""
        # Always keep all demographic questions
        demographic_qs = [q for q in questions if q.category == QuestionCategory.DEMOGRAPHIC]
        other_qs = [q for q in questions if q.category != QuestionCategory.DEMOGRAPHIC]
        
        # Calculate remaining slots
        remaining_slots = max_questions - len(demographic_qs)
        
        if remaining_slots <= 0:
            return demographic_qs
        
        # Prioritize by category and source
        def priority_score(q):
            score = 0
            # Category priority
            if q.category == QuestionCategory.CORE:
                score += 3
            elif q.category == QuestionCategory.ECONOMIC:
                score += 2
            elif q.category == QuestionCategory.SOCIAL:
                score += 1
            
            # Source priority
            if q.source in ['NSS', 'NFHS', 'PLFS', 'ASI']:
                score += 2
            
            # Required questions priority
            if q.required:
                score += 1
            
            return score
        
        other_qs.sort(key=priority_score, reverse=True)
        
        return demographic_qs + other_qs[:remaining_slots]
    
    def _order_questions(self, questions: List[Question]) -> List[Question]:
        """Order questions logically."""
        # Sort by category priority
        category_order = {
            QuestionCategory.DEMOGRAPHIC: 1,
            QuestionCategory.CORE: 2,
            QuestionCategory.ECONOMIC: 3,
            QuestionCategory.SOCIAL: 4,
            QuestionCategory.FOLLOW_UP: 5
        }
        
        return sorted(questions, key=lambda q: category_order.get(q.category, 6))
    
    def _add_routing_logic(self, questions: List[Question]) -> List[Question]:
        """Add routing logic between questions."""
        # Update routing references to use actual question IDs
        for question in questions:
            if question.routing and question.routing.show_if:
                # This would need more sophisticated logic to map references
                pass
        
        return questions
    
    def _create_metadata(self, intent: PromptIntent) -> SurveyMetadata:
        """Create survey metadata."""
        # Determine standard based on domain
        standard_mapping = {
            "labour": "PLFS",
            "health": "NFHS",
            "household": "NSS",
            "enterprise": "ASI",
            "agriculture": "NSS"
        }
        
        standard = standard_mapping.get(intent.domain, "Custom")
        
        return SurveyMetadata(
            standard=standard,
            created_by="SATARK.AI",
            version="1.0",
            gsbpm_phase="design",
            deployment_channels=["web", "mobile_app"],
            deterministic=True,
            auditable=True
        )
    
    def _generate_title(self, intent: PromptIntent) -> str:
        """Generate survey title."""
        parts = []
        
        if intent.audience:
            parts.append(intent.audience.title())
        
        if intent.topic:
            parts.append(intent.topic.title())
        elif intent.domain:
            parts.append(intent.domain.title())
        
        parts.append("Survey")
        
        title = " ".join(parts)
        
        # Ensure reasonable length
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    def _determine_domain(self, intent: PromptIntent) -> SurveyDomain:
        """Determine survey domain."""
        if intent.domain:
            try:
                return SurveyDomain(intent.domain)
            except ValueError:
                pass
        
        return SurveyDomain.HOUSEHOLD  # Default