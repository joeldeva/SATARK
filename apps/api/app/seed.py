from __future__ import annotations

import hashlib
import json
from pathlib import Path

from models.platform import (
    ClassificationCode,
    EnumeratorProfile,
    Household,
    Permission,
    PlatformUser,
    ReferenceDistribution,
    Role,
    ValidationRuleRecord,
)
from models.survey import AdaptiveLogicRecord, Survey
from services.intelligence_adapter import DEFAULT_RULES


PERMISSIONS_BY_ROLE = {
    "admin": ["admin", "survey:read", "survey:write", "collect:write", "coding:review", "validation:review", "dashboard:view"],
    "sdrd": ["survey:read", "survey:write"],
    "fod": ["dashboard:view", "collect:write"],
    "dpd": ["coding:review", "validation:review", "dashboard:view"],
    "scd": ["dashboard:view"],
}


def seed_core_data(db, project_root: Path) -> None:
    seed_path = project_root / "data" / "bootstrap_seed.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        seed = json.load(handle)

    _seed_permissions(db)
    _seed_roles(db)
    _seed_users(db, seed)
    _seed_field_data(db, seed)
    _seed_reference_data(db, seed)
    _seed_validation_rules(db, seed)
    _seed_codes(db, seed)
    _seed_survey_graph(db, seed)
    _seed_adaptive_logic(db, seed)
    db.commit()


def _seed_permissions(db) -> None:
    all_permissions = sorted({permission for values in PERMISSIONS_BY_ROLE.values() for permission in values})
    for code in all_permissions:
        existing = db.query(Permission).filter(Permission.code == code).first()
        if not existing:
            db.add(Permission(code=code, description=code.replace(":", " ")))


def _seed_roles(db) -> None:
    role_names = {
        "admin": "System Admin",
        "sdrd": "Design Officer",
        "fod": "Field Supervisor",
        "dpd": "Processing Officer",
        "scd": "Coordination Officer",
    }
    for code, permissions in PERMISSIONS_BY_ROLE.items():
        role = db.query(Role).filter(Role.code == code).first()
        if role:
            role.permissions = permissions
            role.name = role_names[code]
        else:
            db.add(Role(code=code, name=role_names[code], permissions=permissions))


def _seed_users(db, seed: dict) -> None:
    for user in seed["users"]:
        row = db.query(PlatformUser).filter(PlatformUser.username == user["username"]).first()
        password_hash = _hash_password(user["password"])
        if row:
            row.password_hash = password_hash
            row.role = user["role"]
            row.name = user["name"]
            row.is_active = True
        else:
            db.add(
                PlatformUser(
                    username=user["username"],
                    password_hash=password_hash,
                    role=user["role"],
                    name=user["name"],
                )
            )


def _seed_field_data(db, seed: dict) -> None:
    for enumerator in seed["enumerators"]:
        row = db.get(EnumeratorProfile, enumerator["id"])
        values = {
            "name": enumerator["name"],
            "region": enumerator["region"],
            "assigned": enumerator["assigned"],
            "completed": enumerator["completed"],
            "trust_score": enumerator["trustScore"],
            "trust_level": enumerator["trustLevel"],
            "trust_trend": enumerator["trustTrend"],
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(EnumeratorProfile(id=enumerator["id"], **values))

    for household in seed["households"]:
        row = db.get(Household, household["id"])
        if row:
            row.prepopulated = household["prepop"]
        else:
            db.add(Household(id=household["id"], prepopulated=household["prepop"]))


def _seed_reference_data(db, seed: dict) -> None:
    for key, value in seed.get("referenceDistributions", {}).items():
        row = db.query(ReferenceDistribution).filter(ReferenceDistribution.key == key).first()
        payload = {
            "stratum": "Tamil Nadu urban households" if key == "income" else "all",
            "p05": value.get("p05"),
            "median": value.get("median"),
            "p95": value.get("p95"),
            "params": {},
        }
        if row:
            for field, field_value in payload.items():
                setattr(row, field, field_value)
        else:
            db.add(ReferenceDistribution(key=key, **payload))


def _seed_validation_rules(db, seed: dict) -> None:
    survey_id = seed["survey"]["id"]
    if db.query(ValidationRuleRecord).filter(ValidationRuleRecord.survey_id == survey_id).count():
        return
    for rule in DEFAULT_RULES:
        db.add(
            ValidationRuleRecord(
                survey_id=survey_id,
                field=rule["field"],
                rule_type=rule["rule_type"],
                params=rule["params"],
                severity=rule["severity"],
                reason_template="",
            )
        )


def _seed_codes(db, seed: dict) -> None:
    for code in seed["codes"]:
        row = (
            db.query(ClassificationCode)
            .filter(ClassificationCode.code == code["code"], ClassificationCode.code_type == code["type"])
            .first()
        )
        values = {
            "label": code["label"],
            "synonyms": code.get("synonyms", []),
            "external_source": code.get("externalSource"),
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(ClassificationCode(code=code["code"], code_type=code["type"], **values))


def _seed_survey_graph(db, seed: dict) -> None:
    """Load the bootstrap survey JSON into surveys.question_graph."""
    survey_seed = seed.get("survey")
    if not survey_seed:
        return

    survey_id = survey_seed["id"]
    title_obj = survey_seed.get("title") or {}
    title_en = title_obj.get("en") if isinstance(title_obj, dict) else str(title_obj)
    title = title_en or survey_id

    row = db.query(Survey).filter(Survey.survey_id == survey_id).first()
    payload = {
        "title": title,
        "description": survey_seed.get("description", "Demo employment survey"),
        "domain": survey_seed.get("domain", "labour"),
        "status": survey_seed.get("status", "published"),
        "survey_data": survey_seed,
        "question_graph": survey_seed,
        "version": int(survey_seed.get("version", 1)),
        "created_by": "sdrd",
        "total_questions": len(survey_seed.get("nodes", []) or []),
        "tags": survey_seed.get("tags", []),
    }
    if row:
        for key, value in payload.items():
            setattr(row, key, value)
    else:
        db.add(Survey(survey_id=survey_id, **payload))


def _seed_adaptive_logic(db, seed: dict) -> None:
    """Seed adaptive branches from the bootstrap survey branches field if present."""
    survey_seed = seed.get("survey") or {}
    survey_id = survey_seed.get("id")
    if not survey_id:
        return
    if db.query(AdaptiveLogicRecord).filter(AdaptiveLogicRecord.survey_id == survey_id).count():
        return

    branches = survey_seed.get("branches") or {}
    if isinstance(branches, dict):
        for trigger_field, target_node in branches.items():
            db.add(
                AdaptiveLogicRecord(
                    survey_id=survey_id,
                    trigger={"field": trigger_field},
                    action="branch",
                    target={"node": target_node},
                )
            )


def _hash_password(password: str) -> str:
    """Backwards-compatible hash. JWT verifier accepts both sha256: and bcrypt: prefixes."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
