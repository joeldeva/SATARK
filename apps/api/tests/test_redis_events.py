from app.config import settings
from app.database import SessionLocal, init_db
from app.seed import seed_core_data
from services.response_service import store_collection_response


def test_suspicious_response_emits_flag_created_after_persistence():
    init_db()
    db = SessionLocal()
    published: list[tuple[list[str], dict]] = []

    def fake_publisher(events, payload):
        published.append((events, payload))
        return events

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
            event_publisher=fake_publisher,
        )

        assert result["status"] == "flagged"
        assert published
        assert "response.scored" in published[0][0]
        assert "flag.created" in published[0][0]
        assert published[0][1]["response_id"] == result["responseId"]
    finally:
        db.close()
