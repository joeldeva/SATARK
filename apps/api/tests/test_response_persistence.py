from app.config import settings
from app.database import SessionLocal, init_db
from app.seed import seed_core_data
from models.platform import Paradata, Response, TrustScore, ValidationResult
from services.response_service import store_collection_response


def test_collection_response_persists_verdict_rows():
    init_db()
    db = SessionLocal()
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
        result = store_collection_response(
            db,
            {
                "surveyId": "emp-2026",
                "householdId": "HH-TN-0042",
                "enumeratorId": "ENUM-B",
                "answers": {
                    "occupation": "Unemployed",
                    "income": "200000",
                    "age": "34",
                    "q1": "99",
                    "q2": "99",
                    "q3": "99",
                    "q4": "99",
                },
                "speedMode": "too-fast",
                "elapsedSeconds": 4,
            },
            {"id": "emp-2026", "title": {"en": "Household Employment Survey"}},
        )

        response_id = result["responseId"]
        response = db.get(Response, response_id)
        assert response is not None
        assert response.status == "flagged"
        assert response.trust_level == "Red"

        assert db.query(Paradata).filter(Paradata.response_id == response.id).count() == 1
        trust = db.query(TrustScore).filter(TrustScore.response_id == response.id).one()
        assert trust.risk_level == "Red"
        assert trust.confidence < 50
        assert db.query(ValidationResult).filter(ValidationResult.response_id == response.id).count() >= 2
    finally:
        db.close()
