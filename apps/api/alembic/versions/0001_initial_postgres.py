"""initial postgres schema

Revision ID: 0001_initial_postgres
Revises:
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_postgres"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("permissions", JSONB, nullable=False),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", UUID, sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "enumerators",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(160), nullable=False),
        sa.Column("assigned", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("trust_level", sa.String(16), nullable=False),
        sa.Column("trust_trend", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "households",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("prepopulated", JSONB, nullable=False),
    )

    op.create_table(
        "surveys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50)),
        sa.Column("survey_data", JSONB, nullable=False),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("tags", JSONB),
        sa.Column("total_questions", sa.Integer()),
        sa.Column("prepopulation_rate", sa.Integer()),
    )
    op.create_index("ix_surveys_survey_id", "surveys", ["survey_id"], unique=True)
    op.create_index("ix_surveys_domain", "surveys", ["domain"])
    op.create_index("ix_surveys_status", "surveys", ["status"])

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("respondent_id", sa.String()),
        sa.Column("responses", JSONB, nullable=False),
        sa.Column("coded_responses", JSONB),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("channel", sa.String(50)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("quality_score", sa.Integer()),
        sa.Column("state", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("agent_id", sa.String(100)),
        sa.Column("gps_latitude", sa.String(20)),
        sa.Column("gps_longitude", sa.String(20)),
        sa.Column("is_validated", sa.Boolean()),
        sa.Column("validation_flags", JSONB),
    )
    op.create_index("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])
    op.create_index("ix_survey_responses_agent_id", "survey_responses", ["agent_id"])
    op.create_index("ix_survey_responses_state", "survey_responses", ["state"])
    op.create_index("ix_survey_responses_district", "survey_responses", ["district"])

    op.create_table(
        "generation_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(100)),
        sa.Column("success", sa.Boolean()),
        sa.Column("error_message", sa.Text()),
        sa.Column("processing_time_seconds", sa.Float()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(50)),
    )
    op.create_index("ix_generation_logs_survey_id", "generation_logs", ["survey_id"])

    op.create_table(
        "assignments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("survey_id", sa.String(80), nullable=False),
        sa.Column("enumerator_id", sa.String(64), sa.ForeignKey("enumerators.id"), nullable=False),
        sa.Column("household_id", sa.String(64), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assignments_survey_id", "assignments", ["survey_id"])
    op.create_index("ix_assignments_enumerator_id", "assignments", ["enumerator_id"])
    op.create_index("ix_assignments_household_id", "assignments", ["household_id"])

    op.create_table(
        "responses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("survey_id", sa.String(80), nullable=False),
        sa.Column("enumerator_id", sa.String(64), sa.ForeignKey("enumerators.id"), nullable=True),
        sa.Column("household_id", sa.String(64), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column("prepopulated", JSONB, nullable=False),
        sa.Column("adaptive_log", JSONB, nullable=False),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("trust_level", sa.String(16)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_responses_survey_id", "responses", ["survey_id"])
    op.create_index("ix_responses_enumerator_id", "responses", ["enumerator_id"])
    op.create_index("ix_responses_household_id", "responses", ["household_id"])
    op.create_index("ix_responses_trust_level", "responses", ["trust_level"])
    op.create_index("ix_responses_status", "responses", ["status"])

    op.create_table(
        "response_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("response_id", UUID, sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column("changed_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_response_versions_response_id", "response_versions", ["response_id"])

    op.create_table(
        "paradata",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("response_id", UUID, sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_seconds", sa.Integer()),
        sa.Column("question_timings", JSONB, nullable=False),
        sa.Column("pauses", sa.Integer(), nullable=False),
        sa.Column("correction_count", sa.Integer(), nullable=False),
        sa.Column("back_nav_count", sa.Integer(), nullable=False),
        sa.Column("gps_lat", sa.Float()),
        sa.Column("gps_lng", sa.Float()),
        sa.Column("device", sa.String(120)),
        sa.Column("mode", sa.String(32)),
        sa.Column("network", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_paradata_response_id", "paradata", ["response_id"])

    op.create_table(
        "validation_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("response_id", UUID, sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("layer", sa.String(40), nullable=False),
        sa.Column("field", sa.String(80)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_validation_results_response_id", "validation_results", ["response_id"])

    op.create_table(
        "trust_scores",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("response_id", UUID, sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("breakdown", JSONB, nullable=False),
        sa.Column("fraud_signals", JSONB, nullable=False),
        sa.Column("recommendation", sa.String(40), nullable=False),
        sa.Column("reasons", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trust_scores_response_id", "trust_scores", ["response_id"])
    op.create_index("ix_trust_scores_risk_level", "trust_scores", ["risk_level"])

    op.create_table(
        "coding_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("response_id", UUID, sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("field", sa.String(80), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("suggestions", JSONB, nullable=False),
        sa.Column("approved_code", sa.String(32)),
        sa.Column("approved_label", sa.String(255)),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_coding_results_response_id", "coding_results", ["response_id"])

    op.create_table(
        "validation_rules",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("survey_id", sa.String(80), nullable=False),
        sa.Column("field", sa.String(80), nullable=False),
        sa.Column("rule_type", sa.String(32), nullable=False),
        sa.Column("params", JSONB, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("reason_template", sa.String(255), nullable=False),
    )
    op.create_index("ix_validation_rules_survey_id", "validation_rules", ["survey_id"])

    op.create_table(
        "reference_distributions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("stratum", sa.String(120), nullable=False),
        sa.Column("p05", sa.Float()),
        sa.Column("median", sa.Float()),
        sa.Column("p95", sa.Float()),
        sa.Column("params", JSONB, nullable=False),
    )
    op.create_index("ix_reference_distributions_key", "reference_distributions", ["key"])

    op.create_table(
        "classification_codes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("code_type", sa.String(24), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("synonyms", JSONB, nullable=False),
        sa.Column("external_source", sa.String(120)),
    )
    op.create_index("ix_classification_codes_code", "classification_codes", ["code"])
    op.create_index("ix_classification_codes_code_type", "classification_codes", ["code_type"])

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(120), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "audit_logs",
        "classification_codes",
        "reference_distributions",
        "validation_rules",
        "coding_results",
        "trust_scores",
        "validation_results",
        "paradata",
        "response_versions",
        "responses",
        "assignments",
        "generation_logs",
        "survey_responses",
        "surveys",
        "households",
        "enumerators",
        "users",
        "role_permissions",
        "roles",
        "permissions",
    ):
        op.drop_table(table)
