"""Survey builder that combines rule engine and RAG engine outputs."""

import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from ..models.survey import (
    Survey, Question, QuestionType, QuestionCategory, MultilingualText,
    AnswerOption, ValidationRule, RoutingRule, SurveyDomain, SurveyMetadata,
    SurveyStandard, Language
)
from ..models.prompt import PromptIntent
from .rule_engine import RuleEngine
from .rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class SurveyBuilder:
    """Main survey builder that orchestrates rule engine and RAG engine."""
    
    def __init__(self):
        """Initialize the survey builder."""
        self.rule_engine = RuleEngine()
        self.rag_engine = RAGEngine()
        self.question_counter = 0
    
    def build_survey(self, intent: PromptIntent, max_questions: int = 15) -> Survey:
        """Build a complete survey from intent."""
        logger.info(f"Building survey for intent: {intent.dict()}")
        
        # Reset question counter
        self.question_counter = 0
        
        # Step 1: Generate mandatory demographic questions
        mandatory_questions = self.rule_engine.generate_mandatory_questions(intent)
        self.question_counter = len(mandatory_questions)
        
        # Step 2: Retrieve relevant questions from knowledge base
        remaining_slots = max_questions - len(mandatory_questions)
        if remaining_slots > 0:
            retrieved_questions = self.rag_engine.retrieve_questions(intent, remaining_slots)
            
            # Convert retrieved questions to Question objects
            rag_questions = self._convert_retrieved_questions(retrieved_questions, intent.language)
        else:
            rag_questions = []
        
        # Step 3: Combine and deduplicate questions
        all_questions = mandatory_questions + rag_questions
        all_questions = self._deduplicate_questions(all_questions)
        
        # Step 4: Apply domain-specific rules
        all_questions = self.rule_engine.apply_domain_rules(all_questions, intent)
        
        # Step 5: Add validation rules
        all_questions = self.rule_engine.add_validation_rules(all_questions)
        
        # Step 6: Order questions properly
        all_questions = self.rule_engine.order_questions(all_questions)
        
        # Step 7: Limit to max questions
        if len(all_questions) > max_questions:
            all_questions = all_questions[:max_questions]
        
        # Step 8: Add routing logic
        all_questions = self._add_routing_logic(all_questions)
        
        # Step 9: Create survey metadata
        metadata = self.rule_engine.create_survey_metadata(intent)
        
        # Step 10: Generate survey title
        title = self._generate_survey_title(intent)
        
        # Step 11: Determine survey domain
        domain = self._determine_domain(intent)
        
        # Step 12: Set languages
        languages = [Language(lang) for lang in intent.language if lang in [l.value for l in Language]]
        if not languages:
            languages = [Language.ENGLISH]
        
        # Create the survey
        survey = Survey(
            survey_id=str(uuid.uuid4()),
            title=title,
            domain=domain,
            target_audience=intent.audience,
            language=languages,
            questions=all_questions,
            logic=[],  # Will be populated from routing rules
            metadata=metadata
        )
        
        logger.info(f"Built survey with {len(all_questions)} questions")
        return survey
    
    def _convert_retrieved_questions(self, retrieved_questions: List[Dict], languages: List[str]) -> List[Question]:
        """Convert retrieved question dictionaries to Question objects."""
        questions = []
        
        for q_data in retrieved_questions:
            try:
                self.question_counter += 1
                question = self._create_question_from_data(q_data, languages)
                if question:
                    questions.append(question)
            except Exception as e:
                logger.error(f"Error converting question {q_data.get('id', 'unknown')}: {e}")
                continue
        
        return questions
    
    def _create_question_from_data(self, q_data: Dict, languages: List[str]) -> Optional[Question]:
        """Create a Question object from retrieved data."""
        # Create multilingual text
        question_text = q_data.get('question', {})
        if isinstance(question_text, str):
            question_text = {'en': question_text}
        
        text_dict = {}
        for lang in languages:
            if lang in question_text:
                text_dict[lang] = question_text[lang]
            elif 'en' in question_text:
                text_dict[lang] = question_text['en']  # Fallback to English
        
        if not text_dict:
            return None
        
        text = MultilingualText(**text_dict)
        
        # Determine question type
        q_type = self._map_question_type(q_data.get('type', 'text'))
        
        # Create options if needed
        options = None
        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            options = self._create_options(q_data.get('options', []), languages)
        
        # Create validation
        validation = None
        if 'validation' in q_data:
            validation = ValidationRule(**q_data['validation'])
        
        # Create routing
        routing = None
        if 'routing' in q_data:
            routing_data = q_data['routing']
            routing = RoutingRule(
                condition=routing_data.get('condition'),
                skip_to=routing_data.get('skip_to'),
                show_if=routing_data.get('show_if')
            )
        
        # Determine category
        category = self._map_question_category(q_data.get('category_type', q_data.get('category', 'core')))
        
        return Question(
            id=f"Q{self.question_counter}",
            text=text,
            type=q_type,
            required=q_data.get('required', True),
            options=options,
            validation=validation,
            routing=routing,
            standard_code=q_data.get('id'),  # Use original ID as standard code
            category=category
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
            'matrix': QuestionType.MATRIX
        }
        return mapping.get(type_str, QuestionType.TEXT)
    
    def _map_question_category(self, category_str: str) -> QuestionCategory:
        """Map string category to QuestionCategory enum."""
        mapping = {
            'demographic': QuestionCategory.DEMOGRAPHIC,
            'core': QuestionCategory.CORE,
            'sensitive': QuestionCategory.SENSITIVE,
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
                elif 'en' in label_data:
                    label_dict[lang] = label_data['en']
            
            if label_dict:
                option = AnswerOption(
                    value=opt_data.get('value', ''),
                    label=MultilingualText(**label_dict),
                    code=opt_data.get('code')
                )
                options.append(option)
        
        return options
    
    def _deduplicate_questions(self, questions: List[Question]) -> List[Question]:
        """Remove duplicate questions based on content similarity."""
        unique_questions = []
        seen_texts = set()
        
        for question in questions:
            # Use English text as deduplication key
            text_key = question.text.en.lower().strip()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_questions.append(question)
        
        return unique_questions
    
    def _add_routing_logic(self, questions: List[Question]) -> List[Question]:
        """Add routing logic between questions."""
        # Simple routing logic - can be enhanced
        for i, question in enumerate(questions):
            if question.routing and question.routing.show_if:
                # Update show_if conditions to use actual question IDs
                show_if = question.routing.show_if
                # Replace placeholder IDs with actual IDs
                for j, prev_q in enumerate(questions[:i]):
                    if prev_q.standard_code in show_if:
                        show_if = show_if.replace(prev_q.standard_code, prev_q.id)
                question.routing.show_if = show_if
        
        return questions
    
    def _generate_survey_title(self, intent: PromptIntent) -> str:
        """Generate an appropriate survey title."""
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
        """Determine survey domain from intent."""
        if intent.domain:
            try:
                return SurveyDomain(intent.domain)
            except ValueError:
                pass
        
        # Default to household if can't determine
        return SurveyDomain.HOUSEHOLD