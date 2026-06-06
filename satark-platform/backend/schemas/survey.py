from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class GenerateSurveyRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)
    user_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A survey for rural women about healthcare access with 8 questions",
                "user_id": "officer_123"
            }
        }


class QuestionSchema(BaseModel):
    id: str
    question_number: int
    display_id: str
    text: str
    type: str
    category: Optional[str] = None
    tags: List[str] = []
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None
    required: bool = False
    standard_code: Optional[str] = None


class SurveySchema(BaseModel):
    survey_id: str
    title: str
    description: str
    domain: str
    target_audience: List[str]
    location_type: Optional[str] = None
    languages: List[str]
    version: str
    status: str
    created_at: datetime
    created_by: str
    questions: List[QuestionSchema]
    logic: List[Dict[str, Any]]
    validation_summary: Dict[str, int]
    metadata: Dict[str, Any]


class SurveyListItem(BaseModel):
    survey_id: str
    title: str
    domain: str
    status: str
    created_at: datetime
    total_questions: int
