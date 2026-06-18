from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from models.platform import (
    Assignment,
    ClassificationCode,
    EnumeratorProfile,
    Household,
    MockIdentity,
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
    "sdrd": ["survey:read", "survey:write", "dashboard:view", "collect:write"],
    "fod": ["dashboard:view", "collect:write", "survey:read"],
    "dpd": ["coding:review", "validation:review", "dashboard:view"],
    "scd": ["dashboard:view"],
}


def seed_core_data(db, project_root: Path) -> None:
    seed_path = project_root / "data" / "bootstrap_seed.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        seed = json.load(handle)

    _seed_permissions(db)
    _seed_roles(db)
    db.flush()
    _seed_users(db, seed)
    _seed_field_data(db, seed)
    db.flush()  # ensure enumerators+households exist before assignments FK them
    _seed_reference_data(db, seed)
    _seed_validation_rules(db, seed)
    _seed_codes(db, seed)
    _seed_classification_csvs(db, project_root)
    _seed_survey_graph(db, seed)
    db.flush()  # ensure surveys row exists before adaptive_logic FKs it
    _seed_adaptive_logic(db, seed)
    _seed_assignments(db, seed)
    _seed_mock_identities(db)
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


# Per-stratum monthly household income bands (₹). DEMO-CALIBRATED placeholders
# in the shape of HCES/PLFS factsheets — replace with official stratum values for
# production. Match is value-based so it works across any survey's field ids.
_INCOME_STRATA = [
    {"stratum": "Unemployed households", "match": {"occupation_is": "Unemployed"}, "p05": 0, "median": 3000, "p95": 12000},
    {"stratum": "Student households", "match": {"occupation_is": "Student"}, "p05": 0, "median": 2000, "p95": 15000},
    {"stratum": "Farmer / agricultural households", "match": {"occupation_is": "Farmer"}, "p05": 3000, "median": 12000, "p95": 60000},
    {"stratum": "Salaried households", "match": {"occupation_is": "Salaried"}, "p05": 12000, "median": 32000, "p95": 120000},
    {"stratum": "Self-employed households", "match": {"occupation_is": "Self-employed"}, "p05": 5000, "median": 20000, "p95": 150000},
    {"stratum": "Tamil Nadu households (all)", "match": {}, "p05": 6000, "median": 22000, "p95": 80000},
]


def _seed_reference_data(db, seed: dict) -> None:
    # Stratified income bands.
    for band in _INCOME_STRATA:
        existing = (
            db.query(ReferenceDistribution)
            .filter(ReferenceDistribution.key == "income", ReferenceDistribution.stratum == band["stratum"])
            .first()
        )
        payload = {
            "p05": band["p05"],
            "median": band["median"],
            "p95": band["p95"],
            "params": {"match": band["match"]},
        }
        if existing:
            for field, field_value in payload.items():
                setattr(existing, field, field_value)
        else:
            db.add(ReferenceDistribution(key="income", stratum=band["stratum"], **payload))

    # Any other (non-income) reference keys from the seed file (e.g. response time).
    for key, value in seed.get("referenceDistributions", {}).items():
        if key == "income":
            continue
        row = db.query(ReferenceDistribution).filter(ReferenceDistribution.key == key).first()
        payload = {
            "stratum": "all",
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


def _read_classification_csv(project_root: Path, filename: str) -> list[dict[str, str]]:
    path = project_root / "database" / "database" / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _code_synonyms(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split("|") if item.strip()]


def _upsert_classification_code(db, code: str, code_type: str, values: dict) -> None:
    row = (
        db.query(ClassificationCode)
        .filter(ClassificationCode.code == code, ClassificationCode.code_type == code_type)
        .first()
    )
    if row:
        for key, value in values.items():
            setattr(row, key, value)
    else:
        db.add(ClassificationCode(code=code, code_type=code_type, **values))


def _seed_classification_csvs(db, project_root: Path) -> None:
    """Load official NIC, NCO/NOC, and LGD code CSVs into the SDRD code database."""
    for row in _read_classification_csv(project_root, "nco_parsed.csv"):
        code = (row.get("code") or "").strip()
        if not code:
            continue
        _upsert_classification_code(db, code, "NCO", {
            "label": (row.get("label") or "").strip(),
            "synonyms": _code_synonyms(row.get("synonyms")),
            "external_source": "NCO-2015",
            "family": (row.get("family") or "").strip() or None,
            "sector": (row.get("sector") or "").strip() or None,
            "level": None,
            "section": None,
            "parent_code": None,
        })

    for row in _read_classification_csv(project_root, "nic_parsed.csv"):
        code = (row.get("code") or "").strip()
        if not code:
            continue
        _upsert_classification_code(db, code, "NIC", {
            "label": (row.get("label") or "").strip(),
            "synonyms": _code_synonyms(row.get("synonyms")),
            "external_source": "NIC-2008",
            "family": None,
            "sector": None,
            "level": (row.get("level") or "").strip() or None,
            "section": (row.get("section") or "").strip() or None,
            "parent_code": (row.get("division") or "").strip() or None,
        })

    for row in _read_classification_csv(project_root, "lgd_parsed.csv"):
        code = (row.get("lgd_code") or "").strip()
        if not code:
            continue
        name = (row.get("name_en") or "").strip()
        name_local = (row.get("name_local") or "").strip()
        _upsert_classification_code(db, code, "LGD", {
            "label": name,
            "synonyms": [name_local] if name_local and name_local != name else [],
            "external_source": "LGD",
            "family": (row.get("state_or_ut") or "").strip() or None,
            "sector": None,
            "level": "state",
            "section": None,
            "parent_code": None,
        })

    for row in _read_classification_csv(project_root, "districts_parsed.csv"):
        code = (row.get("district_lgd") or "").strip()
        if not code:
            continue
        _upsert_classification_code(db, code, "LGD_DISTRICT", {
            "label": (row.get("district_name") or "").strip(),
            "synonyms": [],
            "external_source": "LGD",
            "family": None,
            "sector": None,
            "level": "district",
            "section": None,
            "parent_code": (row.get("state_code") or "").strip() or None,
        })


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


def _seed_assignments(db, seed: dict) -> None:
    survey_id = (seed.get("survey") or {}).get("id")
    if not survey_id:
        return
    households = seed.get("households", [])
    enumerators = seed.get("enumerators", [])
    if not households or not enumerators:
        return
    for enumerator in enumerators:
        for household in households:
            existing = (
                db.query(Assignment)
                .filter(
                    Assignment.survey_id == survey_id,
                    Assignment.enumerator_id == enumerator["id"],
                    Assignment.household_id == household["id"],
                )
                .first()
            )
            if existing:
                continue
            db.add(
                Assignment(
                    survey_id=survey_id,
                    enumerator_id=enumerator["id"],
                    household_id=household["id"],
                    status="assigned",
                )
            )


def _seed_mock_identities(db) -> None:
    """DEMO ONLY mock registry — fictitious records, no real Aadhaar/UIDAI."""
    if db.query(MockIdentity).count():
        return
    records = [
        {
            "id_type": "aadhaar", "id_number": "XXXX-XXXX-4242", "last4": "4242",
            "name": "Lakshmi R", "district": "Chennai", "village": "Tiruvanmiyur",
            "lgd_code": "TN-603-0042", "household_size": 4, "last_occupation": "Salaried",
        },
        {
            "id_type": "voter", "id_number": "ABCXXXX7788", "last4": "7788",
            "name": "Murugan S", "district": "Madurai", "village": "Thiruparankundram",
            "lgd_code": "TN-621-0117", "household_size": 5, "last_occupation": "Self-employed",
        },
        {
            "id_type": "ration", "id_number": "TN-XXXX-9090", "last4": "9090",
            "name": "Fatima B", "district": "Coimbatore", "village": "Peelamedu",
            "lgd_code": "TN-641-0090", "household_size": 3, "last_occupation": "Farmer",
        },
    ]
    for rec in records:
        prefill = {
            "name": rec["name"],
            "district": rec["district"],
            "village": rec["village"],
            "lgd_code": rec["lgd_code"],
            "household": rec["household_size"],
            "occupation": rec["last_occupation"],
        }
        db.add(MockIdentity(record=prefill, **rec))


def _hash_password(password: str) -> str:
    """Backwards-compatible hash. JWT verifier accepts both sha256: and bcrypt: prefixes."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
