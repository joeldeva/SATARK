from app.config import settings
from app.database import SessionLocal, init_db
from app.seed import seed_core_data
from services.dashboard_data import analytics_snapshot, enumerators_payload
from services.response_service import store_collection_response


def test_dashboard_reads_persisted_response_data():
    init_db()
    db = SessionLocal()
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
        store_collection_response(
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
            event_publisher=lambda events, payload: events,
        )

        seed_snapshot = {
            "ruralUrban": [33.4, 66.6],
            "genderRatio": {"male": 334, "female": 333},
            "stateValidation": [{"state": "Tamil Nadu", "rate": 91.4}],
            "sectorDistribution": [{"sector": "Labour", "value": 100}],
        }
        snapshot = analytics_snapshot(db, seed_snapshot, {"enumerators": []})

        assert snapshot["totalResponses"] >= 1
        assert snapshot["flagged"] >= 1
        assert snapshot["errorRate"] > 0
        assert enumerators_payload(db, {"enumerators": []})
    finally:
        db.close()
