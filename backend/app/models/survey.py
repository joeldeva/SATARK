"""Survey data models following GSBPM and MoSPI standards."""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class SurveyDomain(str, Enum):
    """MoSPI survey domains."""
    LABOUR = "labour"
    HEALTH = "health"
    EDUCATION = "education"
    AGRICULTURE = "agriculture"
    HOUSEHOLD = "household"
    ENTERPRISE = "enterprise"


class SurveyStandard(str, Enum):
    """Official survey standards."""
    NSS = "NSS"
    NFHS = "NFHS"
    PLFS = "PLFS"
    ASI = "ASI"
    CUSTOM = "Custom"


class QuestionType(str, Enum):
    """Question types supported."""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    TEXT = "text"
    DATE = "date"
    SCALE = "scale"
    MATRIX = "matrix"


class QuestionCategory(str, Enum):
    """Question categories for ordering."""
    DEMOGRAPHIC = "demographic"
    CORE = "core"
    SENSITIVE = "sensitive"
    FOLLOW_UP = "follow_up"


class Language(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    TELUGU = "te"
    TAMIL = "ta"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    ODIA = "or"


class MultilingualText(BaseModel):
    """Text in multiple languages."""
    en: str = Field(..., description="English text")
    hi: Optional[str] = Field(None, description="Hindi text")
    
    class Config:
        extra = "allow"  # Allow other language codes


class AnswerOption(BaseModel):
    """Answer option for choice questions."""
    value: str = Field(..., description="Option value")
    label: MultilingualText = Field(..., description="Option label")
    code: Optional[str] = Field(None, description="Standard classification code")


class ValidationRule(BaseModel):
    """Validation rules for questions."""
    min: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max: Optional[Union[int, float]] = Field(None, description="Maximum value")
    pattern: Optional[str] = Field(None, description="Regex pattern")
    custom_rule: Optional[str] = Field(None, description="Custom validation expression")


class RoutingRule(BaseModel):
    """Question routing and skip logic."""
    condition: Optional[str] = Field(None, description="Condition expression")
    skip_to: Optional[str] = Field(None, description="Question ID to skip to")
    show_if: Optional[str] = Field(None, description="Show condition")


class Question(BaseModel):
    """Survey question model."""
    id: str = Field(..., pattern=r"^Q\d+$", description="Question ID (Q1, Q2, etc.)")
    text: MultilingualText = Field(..., description="Question text")
    type: QuestionType = Field(..., description="Question type")
    required: bool = Field(True, description="Whether question is mandatory")
    options: Optional[List[AnswerOption]] = Field(None, description="Answer options")
    validation: Optional[ValidationRule] = Field(None, description="Validation rules")
    routing: Optional[RoutingRule] = Field(None, description="Routing logic")
    standard_code: Optional[str] = Field(None, description="Official question code")
    category: QuestionCategory = Field(QuestionCategory.CORE, description="Question category")
    
    @validator('options')
    def validate_options(cls, v, values):
        """Validate that choice questions have options."""
        question_type = values.get('type')
        if question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            if not v or len(v) < 2:
                raise ValueError("Choice questions must have at least 2 options")
        return v


class SurveyLogic(BaseModel):
    """Survey-level routing logic."""
    if_condition: str = Field(..., alias="if", description="Condition expression")
    then_action: str = Field(..., alias="then", description="Action to take")
    skip_to: Optional[str] = Field(None, description="Question ID to skip to")


class CrossValidation(BaseModel):
    """Cross-question validation rules."""
    rule: str = Field(..., description="Validation rule expression")
    error_message: MultilingualText = Field(..., description="Error message")
    questions: List[str] = Field(..., description="Question IDs involved")


class SurveyValidation(BaseModel):
    """Survey validation configuration."""
    cross_checks: List[CrossValidation] = Field(default_factory=list)


class SurveyMetadata(BaseModel):
    """Survey metadata."""
    standard: SurveyStandard = Field(..., description="Survey standard")
    created_by: str = Field(..., description="Creator")
    version: str = Field(..., pattern=r"^\d+\.\d+$", description="Version number")
    gsbpm_phase: str = Field("design", description="Current GSBPM phase")
    deployment_channels: List[str] = Field(default_factory=list)
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class Survey(BaseModel):
    """Complete survey model."""
    survey_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique survey ID")
    title: str = Field(..., min_length=5, max_length=200, description="Survey title")
    domain: SurveyDomain = Field(..., description="Survey domain")
    target_audience: Optional[str] = Field(None, description="Target population")
    language: List[Language] = Field(default=[Language.ENGLISH], description="Supported languages")
    questions: List[Question] = Field(..., min_items=1, description="Survey questions")
    logic: List[SurveyLogic] = Field(default_factory=list, description="Survey logic")
    validation: SurveyValidation = Field(default_factory=SurveyValidation)
    metadata: SurveyMetadata = Field(..., description="Survey metadata")
    
    @validator('questions')
    def validate_question_order(cls, v):
        """Ensure proper question ordering."""
        categories = [q.category for q in v]
        # Check if demographics come first
        if categories and categories[0] != QuestionCategory.DEMOGRAPHIC:
            # Auto-reorder if needed
            demographic_qs = [q for q in v if q.category == QuestionCategory.DEMOGRAPHIC]
            other_qs = [q for q in v if q.category != QuestionCategory.DEMOGRAPHIC]
            return demographic_qs + other_qs
        return v
    
    class Config:
        use_enum_values = True
        json_encoders = {
            uuid.UUID: str
        }