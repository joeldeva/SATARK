"""Auto-attached validation rules must fire on LLM-generated surveys too.

Generated surveys use opaque field ids (LAB_001, emp_003 …), not the literal
'occupation'/'income'. The cross-field + context layers must still wire onto the
semantically-detected fields and actually fail a suspicious response — otherwise
fraud silently passes green on every generated survey.
"""
from app.config import settings
from app.database import get_db, init_db
from app.seed import seed_core_data
from app.services.survey_service import create_survey
from app.services.validation_service import ensure_default_validation_rules
from services.response_service import store_collection_response

_NOOP = lambda events, payload: events  # noqa: E731

# A generated-style graph: ids are NOT 'occupation'/'income'.
GENERATED_GRAPH = {
    "id": "gen-labour-1",
    "title": {"en": "Generated Labour Survey"},
    "nodes": [
        {"id": "DEMO_001", "type": "number", "q": {"en": "What is your age?"}, "rules": {"range": [18, 95]}},
        {"id": "LAB_001", "type": "choice", "codeType": "NCO", "q": {"en": "What is your principal occupation?"},
         "options": ["Salaried", "Self-employed", "Unemployed"]},
        {"id": "emp_003", "type": "number", "q": {"en": "Total monthly household income (₹)?"}, "tags": ["income"]},
    ],
    "branches": {},
}


def _seed_db():
    init_db()
    db = next(get_db())
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()


def test_generated_survey_gets_crossfield_and_context_rules():
    _seed_db()
    db = next(get_db())
    try:
        create_survey(db, {"id": "gen-labour-1", "title": {"en": "Generated Labour Survey"}, "question_graph": GENERATED_GRAPH}, "sdrd")
        rules = ensure_default_validation_rules(db, "gen-labour-1", GENERATED_GRAPH)
        by_type = {r["rule_type"]: r for r in rules}
        assert "cross_field" in by_type, "cross-field rule must be attached to a generated survey"
        cf = by_type["cross_field"]["params"]
        assert cf["if_field"] == "LAB_001" and cf["then_field"] == "emp_003"
        assert "context" in by_type and by_type["context"]["params"]["field"] == "emp_003"
    finally:
        db.close()


def test_suspicious_response_on_generated_survey_fires_crossfield():
    _seed_db()
    db = next(get_db())
    try:
        create_survey(db, {"id": "gen-labour-2", "title": {"en": "Generated Labour Survey"}, "question_graph": {**GENERATED_GRAPH, "id": "gen-labour-2"}}, "sdrd")
        ensure_default_validation_rules(db, "gen-labour-2", GENERATED_GRAPH)
        result = store_collection_response(
            db,
            {"surveyId": "gen-labour-2", "answers": {"LAB_001": "Unemployed", "emp_003": 200000, "DEMO_001": 34}, "channel": "web"},
            event_publisher=_NOOP,
        )
        layers = {layer["layer"]: layer for layer in result["intelligence"]["layers"]}
        assert layers["Cross-field"]["status"] == "fail"
        assert "contradicts" in layers["Cross-field"]["reason"].lower()
        # context layer should also flag ₹2,00,000 as out-of-band (warn)
        assert layers["Context"]["status"] in {"warn", "fail"}
    finally:
        db.close()
