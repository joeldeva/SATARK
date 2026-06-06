from fastapi import APIRouter, HTTPException
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

_generator = None
_get_db = None


def set_generator(generator):
    global _generator
    _generator = generator


def set_db_dependency(get_db_func):
    global _get_db
    _get_db = get_db_func


@router.post("/generate")
async def generate_survey(request: dict):
    if not _generator:
        raise HTTPException(status_code=503, detail="Survey generator not initialized")

    prompt = request.get("prompt", "")
    user_id = request.get("user_id")

    if not prompt or len(prompt) < 10:
        raise HTTPException(status_code=400, detail="Prompt must be at least 10 characters")

    start = time.time()
    try:
        survey = _generator.generate(prompt, user_id)
        elapsed = round(time.time() - start, 2)
        _try_save(survey, prompt, user_id, elapsed)
        return {"success": True, "survey": survey, "processing_time": elapsed}
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _try_save(survey, prompt, user_id, elapsed):
    if not _get_db:
        return
    try:
        from models.survey import Survey, GenerationLog
        db = next(_get_db())
        db.add(Survey(
            survey_id=survey["survey_id"],
            title=survey["title"],
            description=survey["description"],
            domain=survey["domain"],
            survey_data=survey,
            created_by=user_id or "system",
            total_questions=len(survey["questions"])
        ))
        db.add(GenerationLog(
            survey_id=survey["survey_id"],
            prompt=prompt,
            user_id=user_id,
            success=True,
            processing_time_seconds=int(elapsed)
        ))
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"DB save skipped: {e}")


@router.get("/surveys")
async def list_surveys():
    if not _get_db:
        return {"surveys": [], "message": "Database not configured"}
    try:
        from models.survey import Survey
        db = next(_get_db())
        surveys = db.query(Survey).order_by(Survey.created_at.desc()).limit(50).all()
        result = [
            {
                "survey_id": s.survey_id,
                "title": s.title,
                "domain": s.domain,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "total_questions": s.total_questions
            }
            for s in surveys
        ]
        db.close()
        return {"surveys": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surveys/{survey_id}")
async def get_survey(survey_id: str):
    if not _get_db:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        from models.survey import Survey
        db = next(_get_db())
        survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
        db.close()
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        return {"survey": survey.survey_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
