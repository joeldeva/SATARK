"""HTTP surface for the assist RAG lane.

Routes:
    POST /api/rag/query   {bucket, question}   survey:read
    POST /api/rag/ingest  multipart            admin
    GET  /api/rag/status                       survey:read
    GET  /api/coding?text=&type=               survey:read

Every response carries top-level ``is_verdict=False`` and ``needs_review=True``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.auth.rbac import get_current_user, require_scope
from app.intelligence.assist.rag.ingest import ingest_bytes
from app.intelligence.assist.rag.service import answer, classify_code
from app.intelligence.assist.rag.store import status as store_status

logger = logging.getLogger(__name__)
router = APIRouter()


_get_db = None


def set_db_dependency(get_db_func):
    global _get_db
    _get_db = get_db_func


def _open_db():
    if not _get_db:
        raise HTTPException(status_code=503, detail="Database not configured")
    return next(_get_db())


@router.get("/rag/status", dependencies=[Depends(require_scope("survey:read"))])
async def rag_status():
    return {**store_status(), "is_verdict": False, "needs_review": True}


@router.post("/rag/query", dependencies=[Depends(require_scope("survey:read"))])
async def rag_query(request: Dict[str, Any]):
    bucket = str(request.get("bucket") or "general").strip().lower()
    question = str(request.get("question") or "").strip()
    k = int(request.get("k") or 5)
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        result = answer(question=question, bucket=bucket, k=k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    # Ensure top-level contract flags regardless of inner shape
    result["is_verdict"] = False
    result["needs_review"] = True
    return result


@router.post("/rag/ingest", dependencies=[Depends(require_scope("admin"))])
async def rag_ingest(
    bucket: str = Form("survey_generation"),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        info = ingest_bytes(
            bucket=bucket,
            filename=file.filename or "upload",
            data=raw,
            mime_type=file.content_type,
            metadata={"uploaded_by": user.get("username")},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Persist KB source row; ingest is incomplete unless metadata is recorded.
    from models.survey import KnowledgeSource

    db = _open_db()
    try:
        db.add(KnowledgeSource(
            bucket=info["bucket"],
            filename=info["filename"],
            mime_type=file.content_type,
            byte_size=info["byte_size"],
            chunk_count=info["chunk_count"],
            uploaded_by=user.get("username"),
            sha256=info["sha256"],
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Knowledge source metadata insert failed: {exc}") from exc
    finally:
        db.close()

    return {
        **info,
        "uploaded_by": user.get("username"),
        "is_verdict": False,
        "needs_review": True,
    }


@router.get("/coding", dependencies=[Depends(require_scope("survey:read"))])
async def coding_retrieval(
    text: str = Query(..., min_length=1),
    type: Optional[str] = Query(default=None, alias="type"),
    k: int = Query(default=5, ge=1, le=20),
):
    """Retrieval-first code lookup (NCO/NIC/COICOP). Assist-only output."""
    result = classify_code(text=text, code_type=type, k=k)

    if not result.get("matches"):
        from models.platform import ClassificationCode

        db = _open_db()
        try:
            query = db.query(ClassificationCode)
            if type:
                query = query.filter(ClassificationCode.code_type == type.upper())
            needle = text.lower()
            rows = query.limit(500).all()
            matches = []
            for row in rows:
                haystack = " ".join([row.label or "", row.code or ""] + list(row.synonyms or [])).lower()
                if needle in haystack:
                    matches.append({
                        "code": row.code,
                        "label": row.label,
                        "type": row.code_type,
                        "score": 0.5,
                        "source": "classification_codes",
                    })
            result["matches"] = matches[:k]
        finally:
            db.close()

    result["is_verdict"] = False
    result["needs_review"] = True
    return result
