import json
import logging
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.jwt import encode_token
from app.auth.password import verify_password
from app.auth.rbac import PERMISSIONS_BY_ROLE, get_current_user, require_scope
from app.config import settings
from services.translation_service import LANGUAGE_NAMES, translate_survey_texts

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


def _open_db():
    if not _get_db:
        raise HTTPException(status_code=503, detail="Database not configured")
    return next(_get_db())


def _question_bank() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[3] / "data" / "question_bank" / "question_bank.json"
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("questions", data if isinstance(data, list) else [])


_STANDARD_QUESTION_TRANSLATIONS: dict[str, dict[str, str]] = {
    "what is your age?": {
        "hi": "\u0906\u092a\u0915\u0940 \u0906\u092f\u0941 \u0915\u094d\u092f\u093e \u0939\u0948?",
        "ta": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0bb5\u0baf\u0ba4\u0bc1 \u0b8e\u0ba9\u0bcd\u0ba9?",
        "te": "\u0c2e\u0c40 \u0c35\u0c2f\u0c38\u0c4d\u0c38\u0c41 \u0c0e\u0c02\u0c24?",
        "kn": "\u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0cb5\u0caf\u0cb8\u0ccd\u0cb8\u0cc1 \u0c8e\u0cb7\u0ccd\u0c9f\u0cc1?",
        "ml": "\u0d28\u0d3f\u0d19\u0d4d\u0d19\u0d33\u0d41\u0d1f\u0d46 \u0d35\u0d2f\u0d38\u0d4d \u0d0e\u0d24\u0d4d\u0d30?",
        "bn": "\u0986\u09aa\u09a8\u09be\u09b0 \u09ac\u09af\u09bc\u09b8 \u0995\u09a4?",
        "gu": "\u0aa4\u0aae\u0abe\u0ab0\u0ac0 \u0a89\u0a82\u0aae\u0ab0 \u0a95\u0ac7\u0a9f\u0ab2\u0ac0 \u0a9b\u0ac7?",
        "pa": "\u0aa4\u0ac1\u0ab9\u0abe\u0aa1\u0ac0 \u0a89\u0aae\u0ab0 \u0a95\u0abf\u0a82\u0aa8\u0ac0 \u0ab9\u0ac8?",
        "mr": "\u0906\u092a\u0932\u0947 \u0935\u092f \u0915\u093f\u0924\u0940 \u0906\u0939\u0947?",
        "ur": "\u0622\u067e \u06a9\u06cc \u0639\u0645\u0631 \u06a9\u06cc\u0627 \u06c1\u06d2\u061f",
    },
    "what is your gender?": {
        "hi": "\u0906\u092a\u0915\u093e \u0932\u093f\u0902\u0917 \u0915\u094d\u092f\u093e \u0939\u0948?",
        "ta": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0baa\u0bbe\u0bb2\u0bbf\u0ba9\u0bae\u0bcd \u0b8e\u0ba9\u0bcd\u0ba9?",
        "te": "\u0c2e\u0c40 \u0c32\u0c3f\u0c02\u0c17\u0c02 \u0c0f\u0c2e\u0c3f\u0c1f\u0c3f?",
        "kn": "\u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0cb2\u0cbf\u0c82\u0c97 \u0caf\u0cbe\u0cb5\u0cc1\u0ca6\u0cc1?",
        "ml": "\u0d28\u0d3f\u0d19\u0d4d\u0d19\u0d33\u0d41\u0d1f\u0d46 \u0d32\u0d3f\u0d02\u0d17\u0d02 \u0d0e\u0d28\u0d4d\u0d24\u0d3e\u0d23\u0d4d?",
        "bn": "\u0986\u09aa\u09a8\u09be\u09b0 \u09b2\u09bf\u0999\u09cd\u0997 \u0995\u09c0?",
        "gu": "\u0aa4\u0aae\u0abe\u0ab0\u0ac1\u0a82 \u0ab2\u0abf\u0a82\u0a97 \u0ab6\u0ac1\u0a82 \u0a9b\u0ac7?",
        "pa": "\u0aa4\u0ac1\u0ab9\u0abe\u0aa1\u0abe \u0ab2\u0abf\u0a82\u0a97 \u0a95\u0ac0 \u0ab9\u0ac8?",
        "mr": "\u0906\u092a\u0932\u093e \u0932\u093f\u0902\u0917 \u0915\u093e\u092f \u0906\u0939\u0947?",
        "ur": "\u0622\u067e \u06a9\u06cc \u062c\u0646\u0633 \u06a9\u06cc\u0627 \u06c1\u06d2\u061f",
    },
    "what is your occupation?": {
        "hi": "\u0906\u092a\u0915\u093e \u0935\u094d\u092f\u0935\u0938\u093e\u092f \u0915\u094d\u092f\u093e \u0939\u0948?",
        "ta": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bca\u0bb4\u0bbf\u0bb2\u0bcd \u0b8e\u0ba9\u0bcd\u0ba9?",
        "te": "\u0c2e\u0c40 \u0c35\u0c43\u0c24\u0c4d\u0c24\u0c3f \u0c0f\u0c2e\u0c3f\u0c1f\u0c3f?",
        "kn": "\u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0c89\u0ca6\u0ccd\u0caf\u0ccb\u0c97 \u0caf\u0cbe\u0cb5\u0cc1\u0ca6\u0cc1?",
        "ml": "\u0d28\u0d3f\u0d19\u0d4d\u0d19\u0d33\u0d41\u0d1f\u0d46 \u0d24\u0d4a\u0d34\u0d3f\u0d7d \u0d0e\u0d28\u0d4d\u0d24\u0d3e\u0d23\u0d4d?",
        "bn": "\u0986\u09aa\u09a8\u09be\u09b0 \u09aa\u09c7\u09b6\u09be \u0995\u09c0?",
        "gu": "\u0aa4\u0aae\u0abe\u0ab0\u0acb \u0ab5\u0acd\u0aaf\u0ab5\u0ab8\u0abe\u0aaf \u0ab6\u0ac1\u0a82 \u0a9b\u0ac7?",
        "pa": "\u0aa4\u0ac1\u0ab9\u0abe\u0aa1\u0abe \u0aaa\u0ac7\u0ab6\u0abe \u0a95\u0ac0 \u0ab9\u0ac8?",
        "mr": "\u0906\u092a\u0932\u093e \u0935\u094d\u092f\u0935\u0938\u093e\u092f \u0915\u093e\u092f \u0906\u0939\u0947?",
        "ur": "\u0622\u067e \u06a9\u0627 \u067e\u06cc\u0634\u06c1 \u06a9\u06cc\u0627 \u06c1\u06d2\u061f",
    },
    "monthly income (\u20b9)?": {
        "hi": "\u092e\u093e\u0938\u093f\u0915 \u0906\u092f (\u20b9)?",
        "ta": "\u0bae\u0bbe\u0ba4\u0bbe\u0ba8\u0bcd\u0ba4\u0bbf\u0bb0 \u0bb5\u0bb0\u0bc1\u0bae\u0bbe\u0ba9\u0bae\u0bcd (\u20b9)?",
        "te": "\u0c28\u0c46\u0c32\u0c35\u0c3e\u0c30\u0c40 \u0c06\u0c26\u0c3e\u0c2f\u0c02 (\u20b9)?",
        "kn": "\u0cae\u0cbe\u0cb8\u0cbf\u0c95 \u0c86\u0ca6\u0cbe\u0caf (\u20b9)?",
        "ml": "\u0d2a\u0d4d\u0d30\u0d24\u0d3f\u0d2e\u0d3e\u0d38 \u0d35\u0d30\u0d41\u0d2e\u0d3e\u0d28\u0d02 (\u20b9)?",
        "bn": "\u09ae\u09be\u09b8\u09bf\u0995 \u0986\u09af\u09bc (\u20b9)?",
        "gu": "\u0aae\u0abe\u0ab8\u0abf\u0a95 \u0a86\u0ab5\u0a95 (\u20b9)?",
        "pa": "\u0aae\u0abe\u0ab8\u0abf\u0a95 \u0a86\u0aae\u0aa6\u0aa8 (\u20b9)?",
        "mr": "\u092e\u093e\u0938\u093f\u0915 \u0909\u0924\u094d\u092a\u0928\u094d\u0928 (\u20b9)?",
        "ur": "\u0645\u0627\u06c1\u0627\u0646\u06c1 \u0622\u0645\u062f\u0646\u06cc (\u20b9)\u061f",
    },
    "household size?": {
        "hi": "\u092a\u0930\u093f\u0935\u093e\u0930 \u0915\u093e \u0906\u0915\u093e\u0930?",
        "ta": "\u0b95\u0bc1\u0b9f\u0bc1\u0bae\u0bcd\u0baa \u0b85\u0bb3\u0bb5\u0bc1?",
        "te": "\u0c07\u0c02\u0c1f\u0c3f \u0c38\u0c2d\u0c4d\u0c2f\u0c41\u0c32 \u0c38\u0c02\u0c16\u0c4d\u0c2f?",
        "kn": "\u0c95\u0cc1\u0c9f\u0cc1\u0c82\u0cac\u0ca6 \u0c97\u0cbe\u0ca4\u0ccd\u0cb0?",
        "ml": "\u0d15\u0d41\u0d1f\u0d41\u0d02\u0d2c\u0d24\u0d4d\u0d24\u0d3f\u0d28\u0d4d\u0d31\u0d46 \u0d35\u0d32\u0d41\u0d2a\u0d4d\u0d2a\u0d02?",
        "bn": "\u09aa\u09b0\u09bf\u09ac\u09be\u09b0\u09c7\u09b0 \u09b8\u09a6\u09b8\u09cd\u09af \u09b8\u0982\u0996\u09cd\u09af\u09be?",
        "gu": "\u0a95\u0ac1\u0a9f\u0ac1\u0a82\u0aac\u0aa8\u0ac1\u0a82 \u0a95\u0aa6?",
        "pa": "\u0aaa\u0ab0\u0abf\u0ab5\u0abe\u0ab0 \u0aa6\u0abe \u0a86\u0a95\u0abe\u0ab0?",
        "mr": "\u0915\u0941\u091f\u0941\u0902\u092c\u093e\u091a\u093e \u0906\u0915\u093e\u0930?",
        "ur": "\u06af\u06be\u0631\u0627\u0646\u06d2 \u06a9\u0627 \u0633\u0627\u0626\u0632\u061f",
    },
}


def _normalize_i18n_key(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _standard_translation(text: str, language: str) -> str | None:
    return _STANDARD_QUESTION_TRANSLATIONS.get(_normalize_i18n_key(text), {}).get(language)


def _normalize_language_codes(values: Any) -> list[str]:
    alias_to_code = {name.lower(): code for code, name in LANGUAGE_NAMES.items()}
    alias_to_code.update({
        "english": "en",
        "hindi": "hi",
        "tamil": "ta",
        "telugu": "te",
        "kannada": "kn",
        "malayalam": "ml",
        "bangla": "bn",
        "bengali": "bn",
        "punjabi": "pa",
        "assamese": "as",
        "odia": "or",
        "oriya": "or",
        "marathi": "mr",
        "urdu": "ur",
    })
    raw_values = values if isinstance(values, list) else [values]
    result: list[str] = []
    for value in raw_values:
        item = str(value or "").strip()
        if not item:
            continue
        code = item if item in LANGUAGE_NAMES else alias_to_code.get(item.lower())
        if code and code not in result:
            result.append(code)
    if "en" not in result:
        result.insert(0, "en")
    return result


@router.post("/auth/login")
async def login(request: Dict[str, Any]):
    from models.platform import PlatformUser

    username = str(request.get("username", "")).strip()
    password = str(request.get("password", ""))
    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    db = _open_db()
    try:
        row = db.query(PlatformUser).filter(PlatformUser.username == username).first()
        if row and row.is_active and verify_password(password, row.password_hash):
            scopes = sorted(PERMISSIONS_BY_ROLE.get(row.role, set()))
            token = encode_token(
                {
                    "sub": row.username,
                    "role": row.role,
                    "name": row.name,
                    "scopes": scopes,
                },
                secret=settings.SECRET_KEY,
            )
            return {
                "user": {"username": row.username, "role": row.role, "name": row.name},
                "token": token,
                "scopes": scopes,
            }
    finally:
        db.close()

    raise HTTPException(status_code=401, detail="Invalid username or password")


@router.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return {
        "user": {"username": user["username"], "role": user["role"], "name": user.get("name", "")},
        "scopes": sorted(user["scopes"]),
        "source": user.get("source", "jwt"),
    }


@router.get("/surveys", dependencies=[Depends(require_scope("survey:read"))])
async def list_surveys(status: str | None = Query(default=None), owner: str | None = Query(default=None)):
    from models.survey import Survey

    db = _open_db()
    try:
        query = db.query(Survey).order_by(Survey.created_at.desc())
        if status:
            query = query.filter(Survey.status == status)
        if owner:
            query = query.filter(Survey.created_by == owner)
        rows = query.limit(200).all()
        surveys = []
        for row in rows:
            surveys.append(_survey_row_to_dict(row))
        return {"surveys": surveys}
    finally:
        db.close()


def _survey_row_to_dict(row) -> Dict[str, Any]:
    """Serialize a Survey row, preferring question_graph (SDRD JSONB) when present."""
    graph = row.question_graph
    if graph:
        base = dict(graph)
        base.setdefault("id", row.survey_id)
        base["status"] = row.status
        base["version"] = row.version
        return base
    data = dict(row.survey_data or {})
    data.setdefault("id", row.survey_id)
    data["status"] = row.status
    data["version"] = row.version
    return data


@router.post("/surveys/generate", dependencies=[Depends(require_scope("survey:write"))])
async def generate_seed_survey(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    if not _generator:
        raise HTTPException(status_code=503, detail="Survey generator not initialized")

    prompt = str(request.get("prompt", "")).strip()
    domain = str(request.get("domain", "")).strip()
    language_code = str(request.get("language", "")).strip()
    language_prompt = str(request.get("language_prompt") or request.get("language_label") or "").strip()
    prompt_parts = [prompt]
    if domain and domain.lower() not in prompt.lower():
        prompt_parts.append(f"Survey Domain: {domain}.")
    if language_code or language_prompt:
        language_text = language_prompt or language_code
        if language_text.lower() not in prompt.lower():
            prompt_parts.append(
                f"Target Language: {language_text} ({language_code}). Generate citizen-facing labels in that language where possible."
            )
    prompt = "\n".join(part for part in prompt_parts if part)
    user_id = request.get("user_id") or user.get("username") or "sdrd"
    if len(prompt) < 10:
        raise HTTPException(status_code=400, detail="Prompt must be at least 10 characters")
    start = time.time()
    try:
        generated = _generator.generate(prompt, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Survey generation assist failed; using deterministic fallback: %s", exc, exc_info=True)
        from services.prompt_parser import PromptParser
        from services.rag_engine import RAGEngine
        from services.rule_engine import RuleEngine
        from services.survey_generator import SurveyGenerator

        generated = SurveyGenerator(PromptParser(), RAGEngine(), RuleEngine()).generate(prompt, user_id)
    elapsed = round(time.time() - start, 3)
    # Log-only: DO NOT create a Survey row. The draft lives in the FE builderStore
    # until the officer explicitly POSTs /api/surveys or PATCHes one (contract).
    _log_generation_only(generated, prompt, user_id, elapsed)
    return {
        "survey": _generated_to_designer_survey(generated),
        "generated": generated,
        "note": "Draft generated by local Gemma assist and trusted SATARK rules - review before publishing",
        "is_verdict": False,
        "needs_review": True,
        "sources": (generated.get("metadata") or {}).get("engine_trace", []),
        "confidence": (generated.get("metadata") or {}).get("llm", {}).get("confidence"),
    }


@router.post("/generate", dependencies=[Depends(require_scope("survey:write"))])
async def generate_survey(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    if not _generator:
        raise HTTPException(status_code=503, detail="Survey generator not initialized")

    prompt = str(request.get("prompt", "")).strip()
    user_id = request.get("user_id") or user.get("username") or "system"

    if len(prompt) < 10:
        raise HTTPException(status_code=400, detail="Prompt must be at least 10 characters")

    start = time.time()
    try:
        survey = _generator.generate(prompt, user_id)
        elapsed = round(time.time() - start, 3)
        _log_generation_only(survey, prompt, user_id, elapsed)
        return {
            "success": True,
            "survey": survey,
            "generated": survey,
            "processing_time": elapsed,
            "is_verdict": False,
            "needs_review": True,
            "note": "Draft generated by local Gemma assist and trusted SATARK rules - review before publishing",
        }
    except Exception as exc:
        logger.error("Generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/surveys/{survey_id}", dependencies=[Depends(require_scope("survey:read"))])
async def get_survey(survey_id: str):
    from models.survey import Survey

    db = _open_db()
    try:
        survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        return {"survey": _survey_row_to_dict(survey)}
    finally:
        db.close()


@router.post("/surveys", dependencies=[Depends(require_scope("survey:write"))])
async def create_survey_endpoint(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from app.services.survey_service import create_survey

    db = _open_db()
    try:
        row = create_survey(db, request, user.get("username") or "sdrd")
        return {"survey": _survey_row_to_dict(row)}
    finally:
        db.close()


@router.patch("/surveys/{survey_id}", dependencies=[Depends(require_scope("survey:write"))])
async def update_survey_endpoint(survey_id: str, request: Dict[str, Any]):
    from app.services.survey_service import update_survey

    db = _open_db()
    try:
        row = update_survey(db, survey_id, request)
        return {"survey": _survey_row_to_dict(row)}
    finally:
        db.close()


@router.post("/surveys/{survey_id}/publish", dependencies=[Depends(require_scope("survey:write"))])
async def publish_survey_endpoint(survey_id: str, request: Dict[str, Any] | None = None, user: dict = Depends(get_current_user)):
    from app.services.survey_service import publish_survey
    from app.services.validation_service import ensure_default_validation_rules
    from models.survey import Survey
    from services.assignment_service import auto_assign_published_survey
    from services.events import publish as publish_event

    request = request or {}
    graph = request.get("question_graph") or request.get("graph")
    if graph is None and (request.get("nodes") is not None or request.get("branches") is not None):
        graph = {
            "id": survey_id,
            "title": request.get("title") or {"en": survey_id},
            "nodes": request.get("nodes") or [],
            "branches": request.get("branches") or {},
        }
    db = _open_db()
    try:
        actor = user.get("username") or "sdrd"
        result = publish_survey(db, survey_id, actor, graph=graph)
        survey_row = db.query(Survey).filter(Survey.survey_id == survey_id).first()
        created_rules = ensure_default_validation_rules(db, survey_id, survey_row.question_graph if survey_row else None)
        assignment = auto_assign_published_survey(db, survey_id, actor)
        result["assignment"] = assignment
        result["validationRulesCreated"] = len(created_rules)
    finally:
        db.close()

    # Best-effort: a missing Redis must not fail an already-committed publish.
    from services.events import RedisPublishError

    try:
        publish_event("survey.published", {
            "survey_id": survey_id,
            "version": result["version"],
            "published_by": user.get("username"),
            "assignment": result.get("assignment"),
        })
    except RedisPublishError as exc:
        logger.warning("survey.published event not delivered (Redis unavailable): %s", exc)
    return result


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

@router.get("/validation-rules", dependencies=[Depends(require_scope("survey:read"))])
async def list_validation_rules_endpoint(survey_id: str | None = Query(default=None)):
    from app.services.validation_service import list_validation_rules

    db = _open_db()
    try:
        return {"rules": list_validation_rules(db, survey_id)}
    finally:
        db.close()


@router.post("/validation-rules", dependencies=[Depends(require_scope("survey:write"))])
async def create_validation_rule_endpoint(request: Dict[str, Any]):
    from app.services.validation_service import create_validation_rule

    db = _open_db()
    try:
        return {"rule": create_validation_rule(db, request)}
    finally:
        db.close()


@router.patch("/validation-rules/{rule_id}", dependencies=[Depends(require_scope("survey:write"))])
async def update_validation_rule_endpoint(rule_id: str, request: Dict[str, Any]):
    from app.services.validation_service import update_validation_rule

    db = _open_db()
    try:
        return {"rule": update_validation_rule(db, rule_id, request)}
    finally:
        db.close()


@router.delete("/validation-rules/{rule_id}", dependencies=[Depends(require_scope("survey:write"))])
async def delete_validation_rule_endpoint(rule_id: str):
    from app.services.validation_service import delete_validation_rule

    db = _open_db()
    try:
        return delete_validation_rule(db, rule_id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Adaptive logic
# ---------------------------------------------------------------------------

@router.get("/adaptive-logic", dependencies=[Depends(require_scope("survey:read"))])
async def list_adaptive_logic_endpoint(survey_id: str | None = Query(default=None)):
    from app.services.validation_service import list_adaptive_logic

    db = _open_db()
    try:
        return {"rules": list_adaptive_logic(db, survey_id)}
    finally:
        db.close()


@router.post("/adaptive-logic", dependencies=[Depends(require_scope("survey:write"))])
async def create_adaptive_logic_endpoint(request: Dict[str, Any]):
    from app.services.validation_service import create_adaptive_logic

    db = _open_db()
    try:
        return {"rule": create_adaptive_logic(db, request)}
    finally:
        db.close()


@router.patch("/adaptive-logic/{rule_id}", dependencies=[Depends(require_scope("survey:write"))])
async def update_adaptive_logic_endpoint(rule_id: str, request: Dict[str, Any]):
    from app.services.validation_service import update_adaptive_logic

    db = _open_db()
    try:
        return {"rule": update_adaptive_logic(db, rule_id, request)}
    finally:
        db.close()



@router.delete("/adaptive-logic/{rule_id}", dependencies=[Depends(require_scope("survey:write"))])
async def delete_adaptive_logic_endpoint(rule_id: str):
    from app.services.validation_service import delete_adaptive_logic

    db = _open_db()
    try:
        return delete_adaptive_logic(db, rule_id)
    finally:
        db.close()


@router.get("/question-bank", dependencies=[Depends(require_scope("survey:read"))])
async def question_bank(q: str | None = Query(default=None), k: int = Query(default=10, ge=1, le=50)):
    from services import question_bank as qb

    if q and q.strip():
        # semantic embedding search (not SQL LIKE)
        return {"questions": qb.search(q.strip(), k=k), "mode": "semantic", "is_verdict": False}
    return {"questions": qb.all_questions(), "mode": "all"}


@router.post("/question-bank", dependencies=[Depends(require_scope("survey:write"))])
async def add_question_bank_entry(request: Dict[str, Any]):
    from services import question_bank as qb

    text = request.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    created = qb.add(request)
    return {"question": created, "is_verdict": False, "needs_review": True}


@router.get("/codes", dependencies=[Depends(require_scope("survey:read"))])
async def codes(
    type: str | None = Query(default=None, alias="type"),
    q: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    section: str | None = Query(default=None),
    parent_code: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=10000),
):
    from sqlalchemy import String as SaString
    from sqlalchemy import cast, or_

    from models.platform import ClassificationCode

    db = _open_db()
    try:
        query = db.query(ClassificationCode)
        if type:
            query = query.filter(ClassificationCode.code_type == type.upper())
        if sector:
            query = query.filter(ClassificationCode.sector == sector)
        if section:
            query = query.filter(ClassificationCode.section == section.upper())
        if parent_code:
            query = query.filter(ClassificationCode.parent_code == parent_code)
        if q:
            needle = f"%{q.strip().lower()}%"
            query = query.filter(or_(
                ClassificationCode.code.ilike(needle),
                ClassificationCode.label.ilike(needle),
                ClassificationCode.family.ilike(needle),
                ClassificationCode.sector.ilike(needle),
                cast(ClassificationCode.synonyms, SaString).ilike(needle),
            ))
        rows = query.order_by(ClassificationCode.code).limit(limit).all()
        results = [
            {
                "code": r.code,
                "type": r.code_type,
                "label": r.label,
                "synonyms": r.synonyms or [],
                "externalSource": r.external_source,
                "family": r.family,
                "sector": r.sector,
                "level": r.level,
                "section": r.section,
                "parentCode": r.parent_code,
            }
            for r in rows
        ]
        return {"codes": results}
    finally:
        db.close()


@router.get("/codes/stats", dependencies=[Depends(require_scope("survey:read"))])
async def code_stats():
    from sqlalchemy import func as sa_func

    from models.platform import ClassificationCode

    db = _open_db()
    try:
        rows = (
            db.query(ClassificationCode.code_type, sa_func.count(ClassificationCode.id))
            .group_by(ClassificationCode.code_type)
            .all()
        )
        stats = {code_type: count for code_type, count in rows}
        stats["total"] = sum(stats.values())

        sectors = (
            db.query(ClassificationCode.sector)
            .filter(ClassificationCode.sector.isnot(None))
            .distinct()
            .all()
        )
        sections = (
            db.query(ClassificationCode.section)
            .filter(ClassificationCode.section.isnot(None))
            .distinct()
            .all()
        )
        return {
            "stats": stats,
            "sectors": sorted(s[0] for s in sectors if s[0]),
            "sections": sorted(s[0] for s in sections if s[0]),
        }
    finally:
        db.close()


@router.get("/llm/status", dependencies=[Depends(require_scope("survey:read"))])
async def llm_status():
    if not _generator or not getattr(_generator, "llm_planner", None):
        return {"enabled": False, "provider": "none"}
    planner = _generator.llm_planner
    provider = getattr(planner, "provider", "ollama")
    return {
        "enabled": True,
        "provider": provider,
        "model": planner.model,
        "baseUrl": planner.base_url,
        "required": planner.required,
        "privacy": "online_openrouter" if provider == "openrouter" else "local_inference_no_external_api",
    }


@router.post("/consent", dependencies=[Depends(require_scope("collect:write"))])
async def consent(request: Dict[str, Any]):
    from models.platform import ConsentRecord

    survey_id = request.get("surveyId") or request.get("survey_id")
    if not survey_id:
        raise HTTPException(status_code=400, detail="surveyId is required")
    db = _open_db()
    try:
        row = ConsentRecord(
            survey_id=str(survey_id),
            household_id=request.get("householdId") or request.get("household_id"),
            enumerator_id=request.get("enumeratorId") or request.get("enumerator_id"),
            consented=bool(request.get("consented", True)),
            language=request.get("language"),
            payload=request,
        )
        db.add(row)
        db.commit()
        return {"ok": True, "consentId": str(row.id), "consented": row.consented}
    finally:
        db.close()


DEMO_IDENTITY_BADGE = "Demo: mock identity registry — no real Aadhaar/UIDAI integration"


@router.post("/prepopulate", dependencies=[Depends(require_scope("collect:write"))])
async def prepopulate(request: Dict[str, Any]):
    """Prefill respondent fields from a MOCK government-ID registry.

    DEMO ONLY: this is a demonstration of the prepopulation PATTERN, not e-KYC.
    No real Aadhaar checksum is validated — any well-formed input is accepted.
    On match, fields are returned with a 'From household record' tag and
    provenance. On no match, we proceed blank with no error.
    """
    from models.platform import Household, MockIdentity

    id_type = str(request.get("id_type") or request.get("idType") or "").strip().lower()
    id_number = str(request.get("id_number") or request.get("idNumber") or "").strip()

    # Back-compat: household lookup still supported when no id supplied.
    if not id_type and not id_number:
        household_id = request.get("householdId") or request.get("household_id")
        db = _open_db()
        try:
            household = db.get(Household, household_id) if household_id else None
            return {
                "matched": bool(household),
                "household": None if not household else {"id": household.id, "prepop": household.prepopulated},
                "demo_badge": DEMO_IDENTITY_BADGE,
                "is_verdict": False,
            }
        finally:
            db.close()

    digits = "".join(ch for ch in id_number if ch.isalnum())
    suffix = digits[-4:] if len(digits) >= 4 else digits
    db = _open_db()
    try:
        query = db.query(MockIdentity)
        if id_type:
            query = query.filter(MockIdentity.id_type == id_type)
        match = query.filter(MockIdentity.last4 == suffix).first() if suffix else None
        if not match:
            # no match -> proceed blank, never an error
            return {
                "matched": False,
                "fields": {},
                "demo_badge": DEMO_IDENTITY_BADGE,
                "is_verdict": False,
                "needs_review": True,
            }
        return {
            "matched": True,
            "id_type": match.id_type,
            "id_number_masked": match.id_number,
            "fields": match.record or {},
            "tag": "From household record",
            "provenance": "Matched mock registry · demo data",
            "demo_badge": DEMO_IDENTITY_BADGE,
            "is_verdict": False,
            "needs_review": True,
        }
    finally:
        db.close()


@router.post("/intelligence/sessions", dependencies=[Depends(require_scope("collect:write"))])
async def intelligence_session(request: Dict[str, Any]):
    from models.platform import IntelligenceSession

    survey_id = request.get("surveyId") or request.get("survey_id")
    if not survey_id:
        raise HTTPException(status_code=400, detail="surveyId is required")
    db = _open_db()
    try:
        row = IntelligenceSession(
            survey_id=str(survey_id),
            household_id=request.get("householdId") or request.get("household_id"),
            enumerator_id=request.get("enumeratorId") or request.get("enumerator_id"),
            payload=request,
        )
        db.add(row)
        db.commit()
        return {"sessionId": str(row.id), "surveyId": row.survey_id, "status": row.status}
    finally:
        db.close()


@router.post("/collection/sessions/start", dependencies=[Depends(require_scope("collect:write"))])
async def collection_session_start(request: Dict[str, Any]):
    from services.collection_service import start_session

    db = _open_db()
    try:
        return start_session(db, request)
    finally:
        db.close()


@router.post("/collection/sessions/{session_id}/answer", dependencies=[Depends(require_scope("collect:write"))])
async def collection_session_answer(session_id: str, request: Dict[str, Any]):
    from services.collection_service import answer_session

    db = _open_db()
    try:
        return answer_session(db, session_id, request)
    finally:
        db.close()


@router.post("/collection/sessions/{session_id}/complete", dependencies=[Depends(require_scope("collect:write"))])
async def collection_session_complete(session_id: str):
    from services.collection_service import complete_session

    db = _open_db()
    try:
        return complete_session(db, session_id)
    finally:
        db.close()


@router.post("/intelligence/answer", dependencies=[Depends(require_scope("collect:write"))])
async def intelligence_answer(request: Dict[str, Any]):
    return _evaluate_intelligence(
        answers=request.get("answers") or {},
        active_question_id=request.get("activeQuestionId"),
        persona=request.get("persona") or "genuine",
        speed_mode=request.get("speedMode") or "normal",
        elapsed_seconds=float(request.get("elapsedSeconds") or 0),
    )


@router.post("/responses", dependencies=[Depends(require_scope("collect:write"))])
async def submit_collection_response(request: Dict[str, Any]):
    from services.response_service import store_collection_response

    db = _open_db()
    try:
        return store_collection_response(db, request)
    finally:
        db.close()


@router.post("/surveys/{survey_id}/responses", dependencies=[Depends(require_scope("collect:write"))])
async def submit_response(survey_id: str, request: Dict[str, Any]):
    from models.survey import Survey
    from services.response_service import store_collection_response

    db = _open_db()
    try:
        survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")

        answers = request.get("answers")
        if answers is None:
            submitted = request.get("responses")
            if not isinstance(submitted, list) or not submitted:
                raise HTTPException(status_code=400, detail="answers or responses must be provided")
            answers = {item.get("question_id"): item.get("value") for item in submitted if item.get("question_id")}
        result = store_collection_response(
            db,
            {
                "surveyId": survey_id,
                "householdId": request.get("householdId") or request.get("respondent_id"),
                "enumeratorId": request.get("enumeratorId") or request.get("agent_id"),
                "answers": answers,
                "channel": request.get("channel", "web"),
                "durationSeconds": request.get("duration_seconds") or request.get("durationSeconds"),
                "gpsLatitude": request.get("gps_latitude") or request.get("gpsLatitude"),
                "gpsLongitude": request.get("gps_longitude") or request.get("gpsLongitude"),
            },
        )
        return {
            "success": result["status"] != "flagged",
            "response_id": result["responseId"],
            "quality_score": result["qualityScore"],
            "trustLevel": result["trustLevel"],
            "status": result["status"],
            "validation_flags": result["intelligence"]["layers"],
        }
    finally:
        db.close()


@router.get("/responses", dependencies=[Depends(require_scope("validation:review"))])
async def responses(status: str | None = Query(default=None)):
    from services.response_service import flagged_responses

    db = _open_db()
    try:
        return {"responses": flagged_responses(db, status=status)}
    finally:
        db.close()


@router.get("/dashboard/flags", dependencies=[Depends(require_scope("dashboard:view"))])
async def dashboard_flags(status: str | None = Query(default="flagged")):
    from services.response_service import flagged_responses

    db = _open_db()
    try:
        return {"responses": flagged_responses(db, status=status)}
    finally:
        db.close()


@router.get("/integrity/verify", dependencies=[Depends(require_scope("dashboard:view"))])
async def integrity_verify():
    from services.hash_chain import verify_chain

    db = _open_db()
    try:
        return verify_chain(db)
    finally:
        db.close()


@router.get("/responses/{response_id}", dependencies=[Depends(require_scope("validation:review"))])
async def response_detail(response_id: str):
    from services.response_service import response_detail as load_response_detail

    db = _open_db()
    try:
        detail = load_response_detail(db, response_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Response not found")
        return detail
    finally:
        db.close()


@router.post("/coding", dependencies=[Depends(require_scope("survey:read"))])
async def coding(request: Dict[str, Any]):
    from models.platform import ClassificationCode

    raw_response = str(request.get("rawResponse") or request.get("raw_response") or "")
    needle = raw_response.strip().lower()
    suggestion = None
    if needle:
        db = _open_db()
        try:
            rows = db.query(ClassificationCode).limit(500).all()
            for row in rows:
                haystack = " ".join([row.label or "", row.code or ""] + list(row.synonyms or [])).lower()
                if needle in haystack:
                    suggestion = {
                        "code": row.code,
                        "type": row.code_type,
                        "label": row.label,
                        "confidence": 93,
                        "source": row.external_source or "classification_codes",
                        "reason": f"Matched persisted {row.code_type} code {row.code}",
                    }
                    break
        finally:
            db.close()
    return {
        "suggestion": suggestion,
        "is_verdict": False,
        "needs_review": True,
    }


@router.post("/coding/review", dependencies=[Depends(require_scope("coding:review"))])
async def coding_review(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from models.platform import AuditLog, CodingResult

    raw_text = str(request.get("rawText") or request.get("raw_text") or request.get("rawResponse") or "")
    field = str(request.get("field") or "occupation")
    coding_id = request.get("id") or request.get("codingResultId") or request.get("coding_result_id")
    db = _open_db()
    try:
        row = db.get(CodingResult, coding_id) if coding_id else None
        if row:
            raw_text = raw_text or row.raw_text
            field = field or row.field
            row.raw_text = raw_text
            row.field = field
            row.suggestions = request.get("suggestions") or row.suggestions or []
            row.approved_code = request.get("approvedCode") or request.get("approved_code") or row.approved_code
            row.approved_label = request.get("approvedLabel") or request.get("approved_label") or row.approved_label
            row.source = str(request.get("source") or "human_review")
            row.confidence = float(request.get("confidence") or (100 if row.approved_code else row.confidence or 0))
            row.needs_review = not bool(request.get("approved") or row.approved_code)
        else:
            row = CodingResult(
                response_id=request.get("responseId") or request.get("response_id"),
                field=field,
                raw_text=raw_text,
                suggestions=request.get("suggestions") or [],
                approved_code=request.get("approvedCode") or request.get("approved_code"),
                approved_label=request.get("approvedLabel") or request.get("approved_label"),
                source=str(request.get("source") or "human_review"),
                confidence=float(request.get("confidence") or (100 if request.get("approvedCode") or request.get("approved_code") else 0)),
                needs_review=not bool(request.get("approved") or request.get("approvedCode") or request.get("approved_code")),
            )
        db.add(row)
        db.flush()
        db.add(
            AuditLog(
                actor=user.get("username") or "dpd",
                action="coding.reviewed" if not row.needs_review else "coding.needs_review",
                entity_type="coding_result",
                entity_id=str(row.id),
                payload=request,
                reason=str(request.get("reason") or "DPD reviewed classification suggestion"),
            )
        )
        db.commit()
        return {"ok": True, "codingResultId": str(row.id), "needsReview": row.needs_review}
    finally:
        db.close()


@router.get("/coding-review", dependencies=[Depends(require_scope("coding:review"))])
async def coding_review_queue(needs_review: bool | None = Query(default=True)):
    from models.platform import CodingResult, Response

    db = _open_db()
    try:
        query = db.query(CodingResult).order_by(CodingResult.created_at.desc())
        if needs_review is not None:
            query = query.filter(CodingResult.needs_review == needs_review)
        payload = []
        for row in query.limit(200).all():
            response = db.get(Response, row.response_id) if row.response_id else None
            suggestions = row.suggestions or []
            top = suggestions[0] if suggestions else None
            payload.append({
                "id": str(row.id),
                "responseId": str(row.response_id) if row.response_id else None,
                "field": row.field,
                "rawText": row.raw_text,
                "suggestions": suggestions,
                "suggested": top,
                "confidence": row.confidence,
                "source": row.source,
                "needsReview": row.needs_review,
                "approvedCode": row.approved_code,
                "approvedLabel": row.approved_label,
                "surveyId": response.survey_id if response else None,
                "enumeratorId": response.enumerator_id if response else None,
                "status": response.status if response else None,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
            })
        return {"items": payload}
    finally:
        db.close()


@router.get("/enumerators", dependencies=[Depends(require_scope("dashboard:view"))])
async def enumerators():
    from services.dashboard_data import enumerators_payload

    db = _open_db()
    try:
        return {"enumerators": enumerators_payload(db)}
    finally:
        db.close()


@router.get("/enumerators/{enumerator_id}", dependencies=[Depends(require_scope("dashboard:view"))])
async def enumerator(enumerator_id: str):
    from services.dashboard_data import enumerator_payload

    db = _open_db()
    try:
        item = enumerator_payload(db, enumerator_id)
    finally:
        db.close()
    if not item:
        raise HTTPException(status_code=404, detail="Enumerator not found")
    return {"enumerator": item}


@router.get("/households", dependencies=[Depends(require_scope("dashboard:view"))])
async def households(region: str | None = Query(default=None)):
    from models.platform import Household

    db = _open_db()
    try:
        payload = []
        for row in db.query(Household).order_by(Household.id.asc()).limit(500).all():
            prepop = row.prepopulated or {}
            if region:
                haystack = " ".join(str(value) for value in prepop.values()).lower()
                if region.lower() not in haystack and region.lower() not in row.id.lower():
                    continue
            payload.append({"id": row.id, "prepop": prepop})
        return {"households": payload}
    finally:
        db.close()


@router.get("/assignments", dependencies=[Depends(require_scope("dashboard:view"))])
async def assignments(
    survey_id: str | None = Query(default=None),
    enumerator_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    from models.platform import Assignment, EnumeratorProfile, Household
    from models.survey import Survey

    db = _open_db()
    try:
        query = db.query(Assignment).order_by(Assignment.created_at.desc())
        if survey_id:
            query = query.filter(Assignment.survey_id == survey_id)
        if enumerator_id:
            query = query.filter(Assignment.enumerator_id == enumerator_id)
        if status:
            query = query.filter(Assignment.status == status)
        rows = query.limit(500).all()
        payload = []
        for row in rows:
            survey = db.query(Survey).filter(Survey.survey_id == row.survey_id).first()
            enumerator_row = db.get(EnumeratorProfile, row.enumerator_id)
            household = db.get(Household, row.household_id) if row.household_id else None
            payload.append({
                "id": str(row.id),
                "surveyId": row.survey_id,
                "surveyTitle": survey.title if survey else row.survey_id,
                "enumeratorId": row.enumerator_id,
                "enumeratorName": enumerator_row.name if enumerator_row else row.enumerator_id,
                "householdId": row.household_id,
                "household": household.prepopulated if household else None,
                "status": row.status,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
            })
        return {"assignments": payload}
    finally:
        db.close()


@router.post("/assignments", dependencies=[Depends(require_scope("dashboard:view"))])
async def create_assignments(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from models.platform import Assignment, AuditLog, EnumeratorProfile, Household
    from models.survey import Survey

    survey_id = str(request.get("surveyId") or request.get("survey_id") or "")
    if not survey_id:
        raise HTTPException(status_code=400, detail="surveyId is required")
    enumerator_ids = request.get("enumeratorIds") or request.get("enumerator_ids") or [request.get("enumeratorId") or request.get("enumerator_id")]
    household_ids = request.get("householdIds") or request.get("household_ids") or [request.get("householdId") or request.get("household_id")]
    enumerator_ids = [str(item) for item in enumerator_ids if item]
    household_ids = [str(item) for item in household_ids if item] or [None]
    if not enumerator_ids:
        raise HTTPException(status_code=400, detail="At least one enumerator is required")

    db = _open_db()
    try:
        survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        if survey.status != "published":
            raise HTTPException(status_code=409, detail="Only published surveys can be assigned")
        created = []
        for enumerator_id in enumerator_ids:
            enumerator_row = db.get(EnumeratorProfile, enumerator_id)
            if not enumerator_row:
                raise HTTPException(status_code=404, detail=f"Enumerator '{enumerator_id}' not found")
            for household_id in household_ids:
                if household_id and not db.get(Household, household_id):
                    raise HTTPException(status_code=404, detail=f"Household '{household_id}' not found")
                row = Assignment(survey_id=survey_id, enumerator_id=enumerator_id, household_id=household_id, status="assigned")
                db.add(row)
                db.flush()
                enumerator_row.assigned = int(enumerator_row.assigned or 0) + 1
                household = db.get(Household, household_id) if household_id else None
                created.append({
                    "id": str(row.id),
                    "surveyId": row.survey_id,
                    "surveyTitle": survey.title,
                    "enumeratorId": row.enumerator_id,
                    "enumeratorName": enumerator_row.name,
                    "householdId": row.household_id,
                    "household": household.prepopulated if household else None,
                    "status": row.status,
                    "createdAt": row.created_at.isoformat() if row.created_at else None,
                })
        db.add(
            AuditLog(
                actor=user.get("username") or "fod",
                action="assignments.created",
                entity_type="survey",
                entity_id=survey_id,
                payload={"assignments": created, "request": request},
                reason=f"Created {len(created)} assignment(s) for published survey {survey_id}",
            )
        )
        db.commit()
        return {"assignments": created}
    finally:
        db.close()


@router.patch("/assignments/{assignment_id}", dependencies=[Depends(require_scope("dashboard:view"))])
async def update_assignment(assignment_id: str, request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from models.platform import Assignment, AuditLog

    status_value = str(request.get("status") or "").strip()
    if not status_value:
        raise HTTPException(status_code=400, detail="status is required")
    db = _open_db()
    try:
        row = db.get(Assignment, assignment_id)
        if not row:
            raise HTTPException(status_code=404, detail="Assignment not found")
        previous = row.status
        row.status = status_value
        db.add(
            AuditLog(
                actor=user.get("username") or "fod",
                action="assignment.status_changed",
                entity_type="assignment",
                entity_id=assignment_id,
                payload={"from": previous, "to": status_value, "request": request},
                reason=f"Assignment moved from {previous} to {status_value}",
            )
        )
        db.commit()
        return {
            "assignment": {
                "id": str(row.id),
                "surveyId": row.survey_id,
                "enumeratorId": row.enumerator_id,
                "householdId": row.household_id,
                "status": row.status,
            }
        }
    finally:
        db.close()


@router.post("/actions", dependencies=[Depends(require_scope("dashboard:view"))])
async def actions(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from models.platform import AuditLog

    action = str(request.get("action") or "action")
    entity_type = str(request.get("entityType") or request.get("entity_type") or "system")
    entity_id = str(request.get("entityId") or request.get("entity_id") or "")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entityId is required")
    db = _open_db()
    try:
        row = AuditLog(
            actor=user.get("username") or "unknown",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=request,
            reason=str(request.get("reason") or ""),
        )
        db.add(row)
        db.commit()
        return {"ok": True, "auditId": str(row.id)}
    finally:
        db.close()


@router.post("/responses/{response_id}/review", dependencies=[Depends(require_scope("validation:review"))])
async def review_response(response_id: str, request: Dict[str, Any], user: dict = Depends(get_current_user)):
    from models.platform import Assignment, AuditLog, Response

    action = str(request.get("action") or "").strip()
    if action not in {"approve", "re_interview", "escalate"}:
        raise HTTPException(status_code=400, detail="action must be approve, re_interview, or escalate")
    db = _open_db()
    try:
        response = db.get(Response, response_id)
        if not response:
            raise HTTPException(status_code=404, detail="Response not found")
        previous = response.status
        response.status = "approved" if action == "approve" else action
        created_assignment = None
        if action == "re_interview":
            assignment = Assignment(
                survey_id=response.survey_id,
                enumerator_id=response.enumerator_id,
                household_id=response.household_id,
                status="assigned",
            )
            db.add(assignment)
            db.flush()
            created_assignment = str(assignment.id)
            if response.enumerator_id:
                from models.platform import EnumeratorProfile

                enumerator = db.get(EnumeratorProfile, response.enumerator_id)
                if enumerator:
                    enumerator.assigned = int(enumerator.assigned or 0) + 1
        db.add(
            AuditLog(
                actor=user.get("username") or "dpd",
                action=f"response.{action}",
                entity_type="response",
                entity_id=response_id,
                payload={"from": previous, "to": response.status, "createdAssignmentId": created_assignment},
                reason=str(request.get("reason") or f"DPD marked response as {response.status}"),
            )
        )
        db.commit()
        return {"ok": True, "responseId": response_id, "status": response.status, "assignmentId": created_assignment}
    finally:
        db.close()


@router.get("/analytics", dependencies=[Depends(require_scope("dashboard:view"))])
async def analytics():
    from services.dashboard_data import analytics_snapshot

    db = _open_db()
    try:
        return analytics_snapshot(db)
    finally:
        db.close()


@router.get("/dashboard/metrics", dependencies=[Depends(require_scope("dashboard:view"))])
async def dashboard_metrics():
    from services.dashboard_data import analytics_snapshot

    db = _open_db()
    try:
        return analytics_snapshot(db)
    finally:
        db.close()


@router.get("/analytics/summary", dependencies=[Depends(require_scope("dashboard:view"))])
async def analytics_summary():
    from models.platform import Response
    from models.survey import Survey

    db = _open_db()
    try:
        surveys = db.query(Survey).all()
        responses = db.query(Response).all()
        validated = sum(1 for response in responses if response.trust_level == "Green")
        domain_counts = Counter(survey.domain for survey in surveys)
        avg_quality = (
            round(sum((response.confidence_score or 0) for response in responses) / len(responses), 1)
            if responses else 0
        )
        return {
            "total_surveys": len(surveys),
            "total_responses": len(responses),
            "validation_rate": round(validated / len(responses) * 100, 1) if responses else 0,
            "average_quality_score": avg_quality,
            "domains": dict(domain_counts),
            "latest_survey": surveys[0].survey_id if surveys else None,
        }
    finally:
        db.close()


@router.get("/analytics/timeseries", dependencies=[Depends(require_scope("dashboard:view"))])
async def analytics_timeseries():
    from models.platform import Response

    db = _open_db()
    try:
        buckets = defaultdict(int)
        for response in db.query(Response).all():
            if response.created_at:
                buckets[response.created_at.date().isoformat()] += 1
        points = [{"date": date, "responses": count} for date, count in sorted(buckets.items())]
        return {"points": points}
    finally:
        db.close()


@router.get("/analytics/agents", dependencies=[Depends(require_scope("dashboard:view"))])
async def analytics_agents():
    from models.platform import Response

    db = _open_db()
    try:
        stats = defaultdict(lambda: {"responses": 0, "validated": 0, "quality_total": 0})
        for response in db.query(Response).all():
            agent = response.enumerator_id or "unassigned"
            stats[agent]["responses"] += 1
            stats[agent]["validated"] += 1 if response.trust_level == "Green" else 0
            stats[agent]["quality_total"] += response.confidence_score or 0

        agents = []
        for agent_id, values in stats.items():
            total = values["responses"]
            agents.append({
                "agent_id": agent_id,
                "responses": total,
                "validation_rate": round(values["validated"] / total * 100, 1) if total else 0,
                "average_quality_score": round(values["quality_total"] / total, 1) if total else 0,
            })
        return {"agents": sorted(agents, key=lambda item: item["responses"], reverse=True)}
    finally:
        db.close()


@router.post("/export", dependencies=[Depends(require_scope("dashboard:view"))])
async def export(request: Dict[str, Any]):
    from models.platform import Response
    from models.survey import Survey

    file_format = request.get("format") or "csv"
    db = _open_db()
    try:
        responses = db.query(Response).order_by(Response.created_at.asc()).all()
        surveys = {row.survey_id: row for row in db.query(Survey).all()}
        rows = ["survey_id,survey_title,response_id,enumerator_id,household_id,status,trust_level,confidence,created_at"]
        for response in responses:
            survey = surveys.get(response.survey_id)
            rows.append(
                ",".join(
                    [
                        _csv(response.survey_id),
                        _csv(survey.title if survey else response.survey_id),
                        _csv(str(response.id)),
                        _csv(response.enumerator_id or ""),
                        _csv(response.household_id or ""),
                        _csv(response.status),
                        _csv(response.trust_level or ""),
                        _csv(str(response.confidence_score or 0)),
                        _csv(response.created_at.isoformat() if response.created_at else ""),
                    ]
                )
            )
        content = "\n".join(rows)
        if file_format == "pdf":
            content = "SATARK Export\n\n" + content
        return {
            "fileName": f"satark-export.{file_format}",
            "content": content,
        }
    finally:
        db.close()


def _log_generation_only(survey: Dict[str, Any], prompt: str, user_id: str, elapsed: float):
    """Persist only the GenerationLog row; do not create a Survey row.

    Honors the SDRD contract: prompt-to-canvas produces a draft held client-side
    until the officer explicitly Creates/Publishes.
    """
    from models.survey import GenerationLog

    db = _open_db()
    try:
        db.add(GenerationLog(
            survey_id=survey.get("survey_id") or "draft",
            prompt=prompt,
            user_id=user_id,
            success=True,
            processing_time_seconds=elapsed,
        ))
        db.commit()
    finally:
        db.close()


def _generated_to_designer_survey(generated: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    languages = _normalize_language_codes(generated.get("languages") or ["en", "hi", "ta"])
    questions = generated.get("questions", [])
    target_languages = [str(language) for language in languages if str(language) != "en"]
    translated_questions: dict[str, list[str]] = {}
    english_questions = [question.get("text") or "Question" for question in questions]
    for language in target_languages:
        translated_questions[language] = translate_survey_texts(english_questions, language)

    for index, question in enumerate(questions):
        validation = question.get("validation") or {}
        question_text = question.get("text") or "Question"
        translations = question.get("translations", {}) or {}
        q_i18n = {
            "en": question_text,
            "hi": translations.get("hi") or _standard_translation(question_text, "hi") or question_text,
            "ta": translations.get("ta") or _standard_translation(question_text, "ta") or question_text,
        }
        for language in languages:
            language_code = str(language)
            translated_list = translated_questions.get(language_code) or []
            model_translation = translated_list[index] if index < len(translated_list) else question_text
            translated_text = (
                translations.get(language_code)
                or _standard_translation(question_text, language_code)
                or model_translation
                or question_text
            )
            if language_code not in q_i18n or q_i18n[language_code] == question_text:
                q_i18n[language_code] = translated_text
        node: dict[str, Any] = {
            "id": question.get("id") or question.get("display_id"),
            "type": _designer_question_type(question.get("type")),
            "q": q_i18n,
        }
        if question.get("standard_code"):
            node["codeType"] = question["standard_code"]
        if question.get("options"):
            option_labels = [
                option.get("label") or option.get("text") or str(option) if isinstance(option, dict) else str(option)
                for option in question["options"]
            ]
            node["options"] = option_labels
            options_i18n = {}
            for language in target_languages:
                options_i18n[language] = translate_survey_texts(option_labels, language)
                if language == "hi":
                    node["options_hi"] = options_i18n[language]
                if language == "ta":
                    node["options_ta"] = options_i18n[language]
            if options_i18n:
                node["options_i18n"] = options_i18n
        if validation.get("min") is not None or validation.get("max") is not None:
            node["rules"] = {
                "range": [
                    validation.get("min", 0),
                    validation.get("max", 999999),
                ]
            }
        trace = question.get("source_trace") or {}
        if trace or question.get("source"):
            node["sourceTrace"] = {
                "source_document": trace.get("source_document") or question.get("source") or "SATARK question bank",
                "section": trace.get("section") or question.get("subdomain") or "Survey module",
                "question_id": trace.get("question_id") or question.get("id") or question.get("display_id"),
                "language": trace.get("language") or ", ".join(LANGUAGE_NAMES.get(language, language) for language in languages),
                "confidence": trace.get("confidence") or question.get("relevance_score") or 80,
                "retrieved_context": trace.get("retrieved_context") or question.get("text") or "",
                "generated_reason": trace.get("generated_reason") or "Included because it matched the survey goal and validation requirements.",
            }
            node["provenance"] = node["sourceTrace"]
        nodes.append(node)

    title = generated.get("title") or "Generated Survey"
    title_i18n = {"en": title, "hi": title, "ta": title}
    for language in target_languages:
        title_i18n[language] = translate_survey_texts([title], language)[0]

    return {
        "id": generated.get("survey_id"),
        "title": title_i18n,
        "nodes": nodes,
        "branches": {},
        "metadata": {
            **(generated.get("metadata", {}) or {}),
            "languages": languages,
            "translation": {
                "provider": settings.TRANSLATION_PROVIDER,
                "model": settings.TRANSLATION_MODEL,
                "privacy": "offline_local" if settings.TRANSLATION_PROVIDER == "ollama" else "configured_provider",
                "target_languages": target_languages,
            },
        },
    }


def _designer_question_type(value: Any) -> str:
    value = str(value or "text").lower()
    if value in {"single_choice", "select_one", "choice"}:
        return "choice"
    if value in {"multiple_choice", "select_many", "multi"}:
        return "multi"
    if value in {"integer", "decimal", "numeric", "number"}:
        return "number"
    if value in {"date"}:
        return "date"
    return "text"


def _csv(value: Any) -> str:
    text = str(value if value is not None else "")
    if any(char in text for char in [",", '"', "\n", "\r"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def _validate_response_payload(survey: Dict[str, Any], responses: list[Dict[str, Any]]) -> list[Dict[str, str]]:
    by_question = {item.get("question_id"): item.get("value") for item in responses}
    flags = []
    for question in survey.get("questions", []):
        question_id = question.get("id")
        value = by_question.get(question_id)
        if question.get("required") and _is_blank(value):
            flags.append({"question_id": question_id, "message": "Required question missing"})
            continue
        validation = question.get("validation") or {}
        if not _is_blank(value) and question.get("type") == "number":
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                flags.append({"question_id": question_id, "message": "Expected numeric value"})
                continue
            minimum = validation.get("min")
            maximum = validation.get("max")
            if minimum is not None and numeric < minimum:
                flags.append({"question_id": question_id, "message": f"Value below minimum {minimum}"})
            if maximum is not None and numeric > maximum:
                flags.append({"question_id": question_id, "message": f"Value above maximum {maximum}"})
    return flags


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == []


def _evaluate_intelligence(
    answers: dict[str, str],
    active_question_id: str | None,
    persona: str,
    speed_mode: str,
    elapsed_seconds: float,
):
    from services.intelligence_adapter import evaluate_intelligence_contract

    return evaluate_intelligence_contract(
        answers=answers,
        active_question_id=active_question_id,
        persona=persona,
        speed_mode=speed_mode,
        elapsed_seconds=elapsed_seconds,
    )

