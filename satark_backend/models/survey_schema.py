"""
SATARK.AI Survey Schema Models
Deterministic survey structure definitions
"""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid
from datetime import datetime


class SurveyDomain(str, Enum):
    """MoSPI survey domains."""
    LABOUR = "labour"
    HEALTH = "health"
    EDUCATION = "education"
    AGRICULTURE = "agriculture"
    HOUSEHOLD = "household"
    ENTERPRISE = "enterprise"
    SOCIAL = "social"
    ECONOMIC = "economic"
    DEMOGRAPHIC = "demographic"


class QuestionType(str, Enum):
    """Supported question types."""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    TEXT = "text"
    DATE = "date"
    SCALE = "scale"
    MATRIX = "matrix"
    BOOLEAN = "boolean"


class QuestionCategory(str, Enum):
    """Question categories for ordering."""
    DEMOGRAPHIC = "demographic"
    CORE = "core"
    ECONOMIC = "economic"
    SOCIAL = "social"
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
    PUNJABI = "pa"
    ASSAMESE = "as"
    URDU = "ur"


class MultilingualText(BaseModel):
    """Text in multiple languages."""
    en: str = Field(..., description="English text")
    hi: Optional[str] = Field(None, description="Hindi text")
    
    class Config:
        extra = "allow"  # Allow other language codes


class AnswerOption(BaseModel):
    """Answer option for choice questions."""
    value: str = Field(..., description="Option value/code")
    label: MultilingualText = Field(..., description="Option label")
    standard_code: Optional[str] = Field(None, description="NCO/NIC/ISIC code")


class ValidationRule(BaseModel):
    """Validation rules for questions."""
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value")
    pattern: Optional[str] = Field(None, description="Regex pattern")
    required: bool = Field(True, description="Whether field is required")
    custom_rule: Optional[str] = Field(None, description="Custom validation expression")


class RoutingRule(BaseModel):
    """Question routing and skip logic."""
    condition: Optional[str] = Field(None, description="Condition expression")
    skip_to: Optional[str] = Field(None, description="Question ID to skip to")
    show_if: Optional[str] = Field(None, description="Show condition")


class Question(BaseModel):
    """Survey question model."""
    id: str = Field(..., description="Question ID")
    text: MultilingualText = Field(..., description="Question text")
    type: QuestionType = Field(..., description="Question type")
    category: QuestionCategory = Field(..., description="Question category")
    required: bool = Field(True, description="Whether question is mandatory")
    options: Optional[List[AnswerOption]] = Field(None, description="Answer options")
    validation: Optional[ValidationRule] = Field(None, description="Validation rules")
    routing: Optional[RoutingRule] = Field(None, description="Routing logic")
    standard_code: Optional[str] = Field(None, description="Official question code")
    tags: List[str] = Field(default_factory=list, description="Question tags")
    source: Optional[str] = Field(None, description="Source (NSS/NFHS/etc)")


class SurveyMetadata(BaseModel):
    """Survey metadata."""
    standard: str = Field(..., description="Survey standard (NSS/NFHS/etc)")
    created_by: str = Field(default="SATARK.AI", description="Creator")
    version: str = Field(default="1.0", description="Version number")
    gsbpm_phase: str = Field(default="design", description="Current GSBPM phase")
    deployment_channels: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    deterministic: bool = Field(default=True, description="Generated deterministically")
    auditable: bool = Field(default=True, description="Fully auditable process")


class Survey(BaseModel):
    """Complete survey model."""
    survey_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=5, max_length=200)
    domain: SurveyDomain = Field(..., description="Survey domain")
    target_audience: Optional[str] = Field(None, description="Target population")
    languages: List[Language] = Field(default=[Language.ENGLISH])
    questions: List[Question] = Field(..., min_items=1)
    metadata: SurveyMetadata = Field(default_factory=SurveyMetadata)
    
    class Config:
        use_enum_values = True


class PromptIntent(BaseModel):
    """Extracted intent from user prompt."""
    domain: Optional[str] = Field(None, description="Survey domain")
    audience: Optional[str] = Field(None, description="Target audience")
    topic: Optional[str] = Field(None, description="Main topic")
    num_questions: Optional[int] = Field(None, description="Requested questions")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    languages: List[str] = Field(default=["en"], description="Requested languages")
    requirements: List[str] = Field(default_factory=list, description="Special requirements")
    confidence: float = Field(default=0.0, description="Classification confidence")


class SurveyGenerationRequest(BaseModel):
    """Request to generate a survey."""
    prompt: str = Field(..., min_length=10, description="Survey description prompt")
    languages: List[str] = Field(default=["en"], description="Target languages")
    max_questions: int = Field(default=15, ge=3, le=50, description="Maximum questions")
    domain: Optional[str] = Field(None, description="Force specific domain")
    standard: Optional[str] = Field(None, description="Force specific standard")
    include_demographics: bool = Field(True, description="Include demographic questions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Survey for rural women about healthcare access with income questions",
                "languages": ["en", "hi"],
                "max_questions": 12,
                "include_demographics": True
            }
        }


class EngineTrace(BaseModel):
    """Engine execution trace for auditability."""
    step: int = Field(..., description="Processing step number")
    engine: str = Field(..., description="Engine name")
    method: str = Field(..., description="Method used")
    output: str = Field(..., description="Output description")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ValidationResult(BaseModel):
    """Survey validation result."""
    score: float = Field(..., description="Validation score (0-100)")
    passed: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    checks_performed: List[str] = Field(default_factory=list, description="Checks performed")


class SurveyGenerationResponse(BaseModel):
    """Response from survey generation."""
    success: bool = Field(..., description="Whether generation succeeded")
    survey: Optional[Dict[str, Any]] = Field(None, description="Generated survey")
    intent: Optional[PromptIntent] = Field(None, description="Extracted intent")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    processing_time: float = Field(..., description="Processing time in seconds")
    engine_trace: List[EngineTrace] = Field(default_factory=list, description="Engine execution trace")
    validation_score: float = Field(default=0.0, description="Validation score")
    deterministic: bool = Field(default=True, description="Deterministic generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "survey": {"survey_id": "...", "title": "Healthcare Access Survey"},
                "intent": {
                    "domain": "health",
                    "audience": "rural women",
                    "topic": "healthcare access"
                },
                "processing_time": 1.23,
                "validation_score": 95.0,
                "deterministic": True
            }
        }