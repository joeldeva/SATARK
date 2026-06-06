"""
SATARK.AI Validation Engine
Statistical validation rules for survey quality assurance
"""

import logging
from typing import List, Dict, Optional
from models.survey_schema import Survey, ValidationResult, Question
from config import QUALITY_THRESHOLDS, GSBPM_PHASES

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Statistical validation engine for survey quality assurance.
    Uses deterministic rules for GSBPM and MoSPI compliance.
    """
    
    def __init__(self):
        """Initialize the validation engine."""
        self.validation_rules = {
            'structure': self._validate_structure,
            'gsbpm_compliance': self._validate_gsbpm_compliance,
            'mospi_standards': self._validate_mospi_standards,
            'question_quality': self._validate_question_quality,
            'accessibility': self._validate_accessibility,
            'deployment_readiness': self._validate_deployment_readiness
        }
    
    def validate_survey(self, survey: Survey) -> ValidationResult:
        """
        Comprehensive survey validation.
        Returns validation score and detailed feedback.
        """
        logger.info(f"🔍 Validating survey: {survey.title}")
        
        errors = []
        warnings = []
        checks_performed = []
        total_score = 0
        max_score = 0
        
        # Run all validation checks
        for check_name, check_function in self.validation_rules.items():
            try:
                result = check_function(survey)
                
                checks_performed.append(check_name)
                total_score += result['score']
                max_score += result['max_score']
                
                errors.extend(result.get('errors', []))
                warnings.extend(result.get('warnings', []))
                
                logger.debug(f"Check {check_name}: {result['score']}/{result['max_score']}")
                
            except Exception as e:
                logger.error(f"Error in validation check {check_name}: {e}")
                errors.append(f"Validation check {check_name} failed: {str(e)}")
        
        # Calculate final score
        final_score = (total_score / max_score * 100) if max_score > 0 else 0
        passed = final_score >= QUALITY_THRESHOLDS['validation_score_min']
        
        logger.info(f"✅ Validation complete: {final_score:.1f}% (passed: {passed})")
        
        return ValidationResult(
            score=round(final_score, 1),
            passed=passed,
            errors=errors,
            warnings=warnings,
            checks_performed=checks_performed
        )
    
    def _validate_structure(self, survey: Survey) -> Dict:
        """Validate survey structure."""
        errors = []
        warnings = []
        score = 0
        max_score = 10
        
        # Check basic structure
        if survey.title and len(survey.title) >= 5:
            score += 2
        else:
            errors.append("Survey title is missing or too short")
        
        if survey.domain:
            score += 2
        else:
            errors.append("Survey domain is not specified")
        
        # Check question count
        question_count = len(survey.questions)
        if 3 <= question_count <= 50:
            score += 3
        elif question_count < 3:
            errors.append("Survey has too few questions (minimum 3)")
        else:
            warnings.append("Survey has many questions (>50), consider reducing")
            score += 1
        
        # Check question IDs are unique
        question_ids = [q.id for q in survey.questions]
        if len(question_ids) == len(set(question_ids)):
            score += 2
        else:
            errors.append("Duplicate question IDs found")
        
        # Check metadata
        if survey.metadata and survey.metadata.standard:
            score += 1
        else:
            warnings.append("Survey standard not specified")
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_gsbpm_compliance(self, survey: Survey) -> Dict:
        """Validate GSBPM compliance."""
        errors = []
        warnings = []
        score = 0
        max_score = 15
        
        # Check GSBPM phase
        if survey.metadata and survey.metadata.gsbpm_phase in GSBPM_PHASES:
            score += 3
        else:
            warnings.append("GSBPM phase not properly specified")
        
        # Check survey metadata completeness
        if survey.metadata:
            if survey.metadata.created_by:
                score += 2
            if survey.metadata.version:
                score += 2
            if survey.metadata.deterministic:
                score += 3
            if survey.metadata.auditable:
                score += 3
        else:
            errors.append("Survey metadata is missing")
        
        # Check question traceability
        traceable_questions = sum(1 for q in survey.questions if q.standard_code or q.source)
        if traceable_questions >= len(survey.questions) * 0.8:
            score += 2
        else:
            warnings.append("Some questions lack traceability (standard codes or sources)")
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_mospi_standards(self, survey: Survey) -> Dict:
        """Validate MoSPI standards compliance."""
        errors = []
        warnings = []
        score = 0
        max_score = 20
        
        # Check demographic questions
        demographic_questions = [q for q in survey.questions if q.category.value == 'demographic']
        if len(demographic_questions) >= 3:
            score += 5
        else:
            errors.append("Insufficient demographic questions (minimum 3 required)")
        
        # Check question ordering (demographics first)
        if survey.questions and survey.questions[0].category.value == 'demographic':
            score += 3
        else:
            warnings.append("Demographic questions should come first")
        
        # Check validation rules
        validated_questions = sum(1 for q in survey.questions if q.validation)
        if validated_questions >= len(survey.questions) * 0.7:
            score += 4
        else:
            warnings.append("Many questions lack validation rules")
            score += 2
        
        # Check multilingual support
        multilingual_questions = sum(1 for q in survey.questions 
                                   if hasattr(q.text, 'hi') and q.text.hi)
        if len(survey.languages) > 1 and multilingual_questions > 0:
            score += 3
        elif len(survey.languages) == 1:
            score += 2
        else:
            warnings.append("Multilingual support could be improved")
        
        # Check standard codes
        coded_questions = sum(1 for q in survey.questions if q.standard_code)
        if coded_questions >= len(survey.questions) * 0.5:
            score += 3
        else:
            warnings.append("Consider adding more standard question codes")
            score += 1
        
        # Check required questions
        required_questions = sum(1 for q in survey.questions if q.required)
        if required_questions >= 3:
            score += 2
        else:
            warnings.append("Consider marking more questions as required")
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_question_quality(self, survey: Survey) -> Dict:
        """Validate individual question quality."""
        errors = []
        warnings = []
        score = 0
        max_score = 15
        
        total_questions = len(survey.questions)
        quality_issues = 0
        
        for question in survey.questions:
            # Check question text length
            if len(question.text.en) < 10:
                quality_issues += 1
                warnings.append(f"Question {question.id} text is very short")
            elif len(question.text.en) > 200:
                quality_issues += 1
                warnings.append(f"Question {question.id} text is very long")
            
            # Check choice questions have adequate options
            if question.type.value in ['single_choice', 'multiple_choice']:
                if not question.options or len(question.options) < 2:
                    quality_issues += 1
                    errors.append(f"Question {question.id} needs at least 2 options")
                elif len(question.options) > 10:
                    quality_issues += 1
                    warnings.append(f"Question {question.id} has many options (>10)")
            
            # Check number questions have validation
            if question.type.value == 'number' and not question.validation:
                quality_issues += 1
                warnings.append(f"Number question {question.id} lacks validation rules")
        
        # Calculate quality score
        if total_questions > 0:
            quality_ratio = 1 - (quality_issues / (total_questions * 2))  # Max 2 issues per question
            score = max(0, int(quality_ratio * max_score))
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_accessibility(self, survey: Survey) -> Dict:
        """Validate accessibility and usability."""
        errors = []
        warnings = []
        score = 0
        max_score = 10
        
        # Check mobile-friendly question types
        mobile_unfriendly = sum(1 for q in survey.questions if q.type.value == 'matrix')
        if mobile_unfriendly == 0:
            score += 3
        else:
            warnings.append(f"{mobile_unfriendly} matrix questions may not be mobile-friendly")
            score += 1
        
        # Check question complexity
        complex_questions = sum(1 for q in survey.questions 
                              if q.options and len(q.options) > 7)
        if complex_questions <= len(survey.questions) * 0.2:
            score += 3
        else:
            warnings.append("Many questions have complex option sets")
            score += 1
        
        # Check language support
        if len(survey.languages) >= 2:
            score += 2
        else:
            warnings.append("Consider adding multilingual support")
        
        # Check sensitive question handling
        sensitive_questions = [q for q in survey.questions if q.category.value == 'economic']
        if sensitive_questions:
            # Check if they're placed appropriately (later in survey)
            sensitive_positions = [i for i, q in enumerate(survey.questions) 
                                 if q.category.value == 'economic']
            if sensitive_positions and min(sensitive_positions) > len(survey.questions) * 0.5:
                score += 2
            else:
                warnings.append("Sensitive questions should be placed later in survey")
        else:
            score += 2  # No sensitive questions is fine
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_deployment_readiness(self, survey: Survey) -> Dict:
        """Validate deployment readiness."""
        errors = []
        warnings = []
        score = 0
        max_score = 10
        
        # Check survey has valid JSON structure
        try:
            survey_dict = survey.dict()
            if survey_dict:
                score += 3
        except Exception as e:
            errors.append(f"Survey JSON serialization failed: {e}")
        
        # Check deployment channels specified
        if survey.metadata and survey.metadata.deployment_channels:
            score += 2
        else:
            warnings.append("No deployment channels specified")
        
        # Check all questions have proper IDs
        if all(q.id for q in survey.questions):
            score += 2
        else:
            errors.append("Some questions lack proper IDs")
        
        # Check routing logic validity
        routing_questions = [q for q in survey.questions if q.routing]
        if routing_questions:
            # Basic routing validation
            score += 2
        else:
            score += 1  # No routing is simpler but acceptable
        
        # Check validation completeness
        if all(q.validation or q.type.value in ['single_choice', 'multiple_choice'] 
               for q in survey.questions):
            score += 1
        
        return {
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings
        }