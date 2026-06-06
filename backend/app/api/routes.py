"""Additional API routes for survey management."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
from pathlib import Path

from ..models.survey import Survey
from config import KNOWLEDGE_BASE_DIR

router = APIRouter()


@router.get("/questions/{domain}")
async def get_questions_by_domain(domain: str):
    """Get all questions for a specific domain."""
    questions_file = KNOWLEDGE_BASE_DIR / "questions" / f"{domain}_questions.json"
    
    if not questions_file.exists():
        raise HTTPException(status_code=404, detail=f"Questions for domain '{domain}' not found")
    
    try:
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        return {
            "domain": domain,
            "questions": questions,
            "count": len(questions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading questions: {str(e)}")


@router.get("/questions")
async def get_all_questions(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    category: Optional[str] = Query(None, description="Filter by category"),
    required_only: bool = Query(False, description="Only required questions")
):
    """Get questions with optional filters."""
    all_questions = []
    
    # Load questions from all domain files
    question_files = [
        "labour_questions.json",
        "health_questions.json",
        "demographic_questions.json"
    ]
    
    for file_name in question_files:
        file_path = KNOWLEDGE_BASE_DIR / "questions" / file_name
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                    all_questions.extend(questions)
            except Exception as e:
                continue
    
    # Apply filters
    filtered_questions = all_questions
    
    if domain:
        filtered_questions = [q for q in filtered_questions if q.get('domain') == domain]
    
    if category:
        filtered_questions = [q for q in filtered_questions if q.get('category') == category]
    
    if required_only:
        filtered_questions = [q for q in filtered_questions if q.get('required', False)]
    
    return {
        "questions": filtered_questions,
        "count": len(filtered_questions),
        "filters": {
            "domain": domain,
            "category": category,
            "required_only": required_only
        }
    }


@router.post("/validate-survey")
async def validate_survey(survey_data: dict):
    """Validate a survey against the schema."""
    try:
        # Try to create Survey object (this validates the schema)
        survey = Survey(**survey_data)
        
        # Additional validation checks
        warnings = []
        errors = []
        
        # Check question count
        if len(survey.questions) < 3:
            warnings.append("Survey has fewer than 3 questions")
        elif len(survey.questions) > 50:
            errors.append("Survey has more than 50 questions")
        
        # Check for demographic questions
        demographic_questions = [q for q in survey.questions if q.category.value == "demographic"]
        if not demographic_questions:
            warnings.append("No demographic questions found")
        
        # Check question ordering
        categories = [q.category.value for q in survey.questions]
        if categories and categories[0] != "demographic":
            warnings.append("Demographic questions should come first")
        
        # Check for required questions without validation
        for question in survey.questions:
            if question.required and question.type.value == "number" and not question.validation:
                warnings.append(f"Required number question {question.id} has no validation")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "survey_id": survey.survey_id,
            "question_count": len(survey.questions)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "survey_id": None,
            "question_count": 0
        }


@router.get("/templates")
async def get_survey_templates():
    """Get available survey templates."""
    templates = [
        {
            "id": "labour_basic",
            "name": "Basic Labour Survey",
            "description": "Standard employment and occupation questions",
            "domain": "labour",
            "question_count": 8,
            "languages": ["en", "hi"]
        },
        {
            "id": "health_access",
            "name": "Healthcare Access Survey", 
            "description": "Healthcare facility access and satisfaction",
            "domain": "health",
            "question_count": 6,
            "languages": ["en", "hi"]
        },
        {
            "id": "demographic_standard",
            "name": "Standard Demographics",
            "description": "Basic demographic information collection",
            "domain": "all",
            "question_count": 5,
            "languages": ["en", "hi"]
        }
    ]
    
    return {
        "templates": templates,
        "count": len(templates)
    }


@router.get("/export/{survey_id}")
async def export_survey(
    survey_id: str,
    format: str = Query("json", description="Export format: json, csv, xlsx")
):
    """Export survey in different formats."""
    # This would typically load the survey from a database
    # For now, return a placeholder response
    
    if format not in ["json", "csv", "xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported export format")
    
    return {
        "survey_id": survey_id,
        "format": format,
        "download_url": f"/downloads/{survey_id}.{format}",
        "message": "Export functionality would be implemented here"
    }