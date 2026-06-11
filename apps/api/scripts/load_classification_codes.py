"""Load NCO, NIC, LGD, and District CSV data into classification_codes.

Run from the apps/api directory:
    python scripts/load_classification_codes.py

Idempotent — upserts by (code, code_type) natural key.
"""

import csv
import logging
import sys
from pathlib import Path

# Ensure apps/api is on the path for model imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from models.platform import ClassificationCode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATABASE_DIR = Path(__file__).resolve().parents[3].parent / "database (1)" / "database"


def _read_csv(filename: str) -> list[dict]:
    path = DATABASE_DIR / filename
    if not path.exists():
        logger.warning("CSV not found: %s", path)
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _synonyms_list(raw: str) -> list[str]:
    """Parse pipe-delimited synonyms into a list."""
    if not raw or not raw.strip():
        return []
    return [s.strip() for s in raw.split("|") if s.strip()]


def _upsert(db, code: str, code_type: str, **fields) -> bool:
    """Upsert a single code row. Returns True if a new row was created."""
    row = (
        db.query(ClassificationCode)
        .filter(ClassificationCode.code == code, ClassificationCode.code_type == code_type)
        .first()
    )
    if row:
        for key, value in fields.items():
            setattr(row, key, value)
        return False
    else:
        db.add(ClassificationCode(code=code, code_type=code_type, **fields))
        return True


def load_nco(db) -> int:
    rows = _read_csv("nco_parsed.csv")
    created = 0
    for row in rows:
        code = (row.get("code") or "").strip()
        if not code:
            continue
        is_new = _upsert(
            db,
            code=code,
            code_type="NCO",
            label=(row.get("label") or "").strip(),
            synonyms=_synonyms_list(row.get("synonyms", "")),
            external_source="NCO-2015",
            family=(row.get("family") or "").strip() or None,
            sector=(row.get("sector") or "").strip() or None,
            level=None,
            section=None,
            parent_code=None,
        )
        if is_new:
            created += 1
    logger.info("NCO: %d rows processed, %d new", len(rows), created)
    return len(rows)


def load_nic(db) -> int:
    rows = _read_csv("nic_parsed.csv")
    created = 0
    for row in rows:
        code = (row.get("code") or "").strip()
        if not code:
            continue
        level = (row.get("level") or "").strip() or None
        section_val = (row.get("section") or "").strip() or None
        division = (row.get("division") or "").strip() or None
        is_new = _upsert(
            db,
            code=code,
            code_type="NIC",
            label=(row.get("label") or "").strip(),
            synonyms=_synonyms_list(row.get("synonyms", "")),
            external_source="NIC-2008",
            family=None,
            sector=None,
            level=level,
            section=section_val,
            parent_code=division,
        )
        if is_new:
            created += 1
    logger.info("NIC: %d rows processed, %d new", len(rows), created)
    return len(rows)


def load_lgd(db) -> int:
    rows = _read_csv("lgd_parsed.csv")
    created = 0
    for row in rows:
        code = (row.get("lgd_code") or "").strip()
        if not code:
            continue
        name = (row.get("name_en") or "").strip()
        name_local = (row.get("name_local") or "").strip()
        synonyms = [name_local] if name_local and name_local != name else []
        state_or_ut = (row.get("state_or_ut") or "").strip() or None
        is_new = _upsert(
            db,
            code=code,
            code_type="LGD",
            label=name,
            synonyms=synonyms,
            external_source="LGD",
            family=state_or_ut,
            sector=None,
            level="state",
            section=None,
            parent_code=None,
        )
        if is_new:
            created += 1
    logger.info("LGD: %d rows processed, %d new", len(rows), created)
    return len(rows)


def load_districts(db) -> int:
    rows = _read_csv("districts_parsed.csv")
    created = 0
    for row in rows:
        code = (row.get("district_lgd") or "").strip()
        if not code:
            continue
        is_new = _upsert(
            db,
            code=code,
            code_type="LGD_DISTRICT",
            label=(row.get("district_name") or "").strip(),
            synonyms=[],
            external_source="LGD",
            family=None,
            sector=None,
            level="district",
            section=None,
            parent_code=(row.get("state_code") or "").strip() or None,
        )
        if is_new:
            created += 1
    logger.info("LGD_DISTRICT: %d rows processed, %d new", len(rows), created)
    return len(rows)


def main():
    logger.info("Loading classification codes from %s", DATABASE_DIR)
    if not DATABASE_DIR.exists():
        logger.error("Database directory not found: %s", DATABASE_DIR)
        sys.exit(1)

    db = SessionLocal()
    try:
        total = 0
        total += load_nco(db)
        total += load_nic(db)
        total += load_lgd(db)
        total += load_districts(db)
        db.commit()
        logger.info("SUCCESS — %d total classification codes loaded", total)
    except Exception:
        db.rollback()
        logger.exception("Failed to load classification codes")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
