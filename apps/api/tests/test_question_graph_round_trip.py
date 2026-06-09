"""survey_service create -> update -> publish round-trip on an in-memory SQLite DB."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make sure we can import the FastAPI app modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base
import models.platform  # noqa: F401  (register tables)
import models.survey  # noqa: F401
from app.services.survey_service import create_survey, get_survey, publish_survey, update_survey


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_patch_publish_round_trip(db):
    payload = {
        "id": "test-survey-001",
        "title": {"en": "Test Survey"},
        "domain": "labour",
        "question_graph": {
            "id": "test-survey-001",
            "title": {"en": "Test Survey"},
            "nodes": [
                {"id": "age", "type": "number", "q": {"en": "Age?"}},
            ],
            "branches": {},
        },
    }
    created = create_survey(db, payload, "sdrd")
    assert created.status == "draft"
    assert created.version == 1
    assert (created.question_graph or {}).get("nodes")

    # PATCH: replace nodes
    updated_graph = {
        "id": "test-survey-001",
        "title": {"en": "Test Survey"},
        "nodes": [
            {"id": "age", "type": "number", "q": {"en": "Age?"}},
            {"id": "name", "type": "text", "q": {"en": "Name?"}},
        ],
        "branches": {},
    }
    updated = update_survey(db, "test-survey-001", {"question_graph": updated_graph})
    assert len(updated.question_graph["nodes"]) == 2
    assert updated.status == "draft"

    # PUBLISH: status -> published, version bumped
    result = publish_survey(db, "test-survey-001", "sdrd")
    assert result["status"] == "published"
    assert result["version"] == 1  # first publish keeps version
    row = get_survey(db, "test-survey-001")
    assert row.status == "published"

    # Re-publish bumps version
    # First re-open by setting back to draft would require a separate endpoint;
    # the publish_survey itself when already-published bumps version
    result2 = publish_survey(db, "test-survey-001", "sdrd")
    assert result2["version"] == 2
