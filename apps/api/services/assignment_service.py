from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from models.platform import Assignment, AuditLog, EnumeratorProfile, Household
from models.survey import Survey


def auto_assign_published_survey(db, survey_id: str, actor: str) -> dict[str, Any]:
    survey = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "published":
        raise HTTPException(status_code=409, detail="Only published surveys can be assigned")

    existing = (
        db.query(Assignment)
        .filter(Assignment.survey_id == survey_id)
        .order_by(Assignment.created_at.desc())
        .first()
    )
    if existing:
        return _assignment_to_api(db, existing, auto_created=False)

    enumerators = db.query(EnumeratorProfile).order_by(EnumeratorProfile.id.asc()).all()
    if not enumerators:
        raise HTTPException(status_code=409, detail="No field agents available for assignment")

    enumerator = min(
        enumerators,
        key=lambda row: (
            int(row.assigned or 0) - int(row.completed or 0),
            -(row.trust_score or 0),
            row.id,
        ),
    )
    household = db.query(Household).order_by(Household.id.asc()).first()
    assignment = Assignment(
        survey_id=survey_id,
        enumerator_id=enumerator.id,
        household_id=household.id if household else None,
        status="assigned",
    )
    db.add(assignment)
    db.flush()
    enumerator.assigned = int(enumerator.assigned or 0) + 1
    db.add(
        AuditLog(
            actor=actor,
            action="assignment.auto_created",
            entity_type="survey",
            entity_id=survey_id,
            payload={"assignmentId": str(assignment.id), "enumeratorId": enumerator.id, "householdId": assignment.household_id},
            reason=f"Published survey {survey_id} was automatically assigned to {enumerator.name}",
        )
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_to_api(db, assignment, auto_created=True)


def _assignment_to_api(db, assignment: Assignment, auto_created: bool) -> dict[str, Any]:
    survey = db.query(Survey).filter(Survey.survey_id == assignment.survey_id).first()
    enumerator = db.get(EnumeratorProfile, assignment.enumerator_id)
    household = db.get(Household, assignment.household_id) if assignment.household_id else None
    return {
        "id": str(assignment.id),
        "surveyId": assignment.survey_id,
        "surveyTitle": survey.title if survey else assignment.survey_id,
        "enumeratorId": assignment.enumerator_id,
        "enumeratorName": enumerator.name if enumerator else assignment.enumerator_id,
        "householdId": assignment.household_id,
        "household": household.prepopulated if household else None,
        "status": assignment.status,
        "createdAt": assignment.created_at.isoformat() if assignment.created_at else None,
        "autoCreated": auto_created,
    }
