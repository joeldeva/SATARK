"""Survey CRUD + publish — pure SQLAlchemy, no intelligence imports.

Boundary contract: this module MUST NOT import from app.intelligence.verdict.*.
A test (tests/test_import_boundary.py) enforces this.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.survey import Survey, SurveyVersion


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _extract_title(payload: Dict[str, Any]) -> str:
    title = payload.get("title")
    if isinstance(title, dict):
        return title.get("en") or next(iter(title.values()), "Untitled Survey")
    return str(title) if title else "Untitled Survey"


def create_survey(db: Session, payload: Dict[str, Any], user_id: str) -> Survey:
    survey_id = (payload.get("id") or payload.get("survey_id") or f"sdrd-{uuid4().hex[:10]}").strip()
    if db.query(Survey).filter(Survey.survey_id == survey_id).first():
        raise HTTPException(status_code=409, detail=f"Survey '{survey_id}' already exists")

    title = _extract_title(payload)
    graph = payload.get("question_graph") or payload.get("graph") or {
        "id": survey_id,
        "title": payload.get("title") or {"en": title},
        "nodes": payload.get("nodes") or [],
        "branches": payload.get("branches") or {},
    }
    row = Survey(
        survey_id=survey_id,
        title=title,
        description=payload.get("description", ""),
        domain=payload.get("domain", "general"),
        status="draft",
        survey_data=graph,
        question_graph=graph,
        version=1,
        created_by=user_id,
        tags=payload.get("tags") or [],
        total_questions=len((graph.get("nodes") or []) if isinstance(graph, dict) else []),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_survey(db: Session, survey_id: str, payload: Dict[str, Any]) -> Survey:
    row = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Survey not found")
    if row.status == "published":
        raise HTTPException(status_code=409, detail="Cannot edit a published survey; create a new draft")

    if "question_graph" in payload or "nodes" in payload or "branches" in payload:
        graph = payload.get("question_graph")
        if graph is None:
            graph = {
                "id": survey_id,
                "title": payload.get("title") or row.title,
                "nodes": payload.get("nodes") or (row.question_graph or {}).get("nodes", []),
                "branches": payload.get("branches") or (row.question_graph or {}).get("branches", {}),
            }
        row.question_graph = graph
        row.survey_data = graph
        if isinstance(graph, dict):
            row.total_questions = len(graph.get("nodes") or [])

    if "title" in payload:
        row.title = _extract_title(payload)
    if "description" in payload:
        row.description = payload["description"]
    if "tags" in payload:
        row.tags = payload["tags"] or []
    if "domain" in payload:
        row.domain = payload["domain"]

    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return row


def publish_survey(db: Session, survey_id: str, user_id: str) -> Dict[str, Any]:
    row = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Survey not found")
    graph = row.question_graph or row.survey_data
    if not graph:
        raise HTTPException(status_code=409, detail="Cannot publish empty survey")

    new_version = (row.version or 1) + 1 if row.status == "published" else (row.version or 1)

    snapshot = SurveyVersion(
        survey_id=survey_id,
        version=new_version,
        question_graph=graph,
        published_by=user_id,
    )
    db.add(snapshot)

    row.status = "published"
    row.version = new_version
    row.published_at = _now()
    db.commit()
    db.refresh(row)

    return {
        "survey_id": survey_id,
        "status": row.status,
        "version": row.version,
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }


def get_survey(db: Session, survey_id: str) -> Optional[Survey]:
    return db.query(Survey).filter(Survey.survey_id == survey_id).first()
