"""Prompt parsing and intent extraction models."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class PromptIntent(BaseModel):
    """Extracted intent from user prompt."""
    audience: Optional[str] = Field(None, description="Target audience (e.g., 'rural women')")
    domain: Optional[str] = Field(None, description="Survey domain")
    topic: Optional[str] = Field(None, description="Main topic")
    num_questions: Optional[int] = Field(None, description="Requested number of questions")
    keywords: List[str] = Field(default_factory=list, description="Key terms extracted")
    language: List[str] = Field(default=["en"], description="Requested languages")
    special_requirements: List[str] = Field(default_factory=list, description="Special needs")
    
    @validator('num_questions')
    def validate_question_count(cls, v):
        """Validate question count is reasonable."""
        if v is not None and (v < 3 or v > 50):
            raise ValueError("Number of questions must be between 3 and 50")
        return v


class GenerationRequest(BaseModel):
    """Request to generate a survey."""
    prompt: str = Field(..., min_length=10, description="User prompt describing the survey")
    language: List[str] = Field(default=["en"], description="Target languages")
    max_questions: int = Field(default=15, ge=3, le=50, description="Maximum questions")
    domain: Optional[str] = Field(None, description="Force specific domain")
    standard: Optional[str] = Field(None, description="Force specific standard")
    include_demographics: bool = Field(True, description="Include demographic questions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A survey for rural women about access to healthcare with 8 questions, include income and satisfaction",
                "language": ["en", "hi"],
                "max_questions": 10,
                "include_demographics": True
            }
        }


class GenerationResponse(BaseModel):
    """Response from survey generation."""
    success: bool = Field(..., description="Whether generation succeeded")
    survey: Optional[Dict[str, Any]] = Field(None, description="Generated survey JSON")
    intent: Optional[PromptIntent] = Field(None, description="Extracted intent")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings or suggestions")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "survey": {"survey_id": "...", "title": "Healthcare Access Survey"},
                "intent": {
                    "audience": "rural women",
                    "domain": "health",
                    "topic": "access",
                    "num_questions": 8
                },
                "errors": [],
                "warnings": ["Consider adding age validation"],
                "processing_time": 1.23
            }
        }