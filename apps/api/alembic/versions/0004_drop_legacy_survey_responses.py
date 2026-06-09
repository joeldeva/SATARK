"""drop legacy survey_responses table

Revision ID: 0004_drop_legacy_survey_responses
Revises: 0003_collection_operations
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0004_drop_legacy_survey_responses"
down_revision = "0003_collection_operations"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            type_=sa.String(64),
            existing_type=sa.String(32),
        )
    inspector = inspect(op.get_bind())
    if "survey_responses" not in inspector.get_table_names():
        return
    index_names = {item["name"] for item in inspector.get_indexes("survey_responses")}
    for index_name in (
        "ix_survey_responses_district",
        "ix_survey_responses_state",
        "ix_survey_responses_agent_id",
        "ix_survey_responses_survey_id",
    ):
        if index_name in index_names:
            op.drop_index(index_name, table_name="survey_responses")
    op.drop_table("survey_responses")


def downgrade() -> None:
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("respondent_id", sa.String(), nullable=True),
        sa.Column("responses", JSONB, nullable=False),
        sa.Column("coded_responses", JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("gps_latitude", sa.String(20), nullable=True),
        sa.Column("gps_longitude", sa.String(20), nullable=True),
        sa.Column("is_validated", sa.Boolean(), nullable=True),
        sa.Column("validation_flags", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])
    op.create_index("ix_survey_responses_agent_id", "survey_responses", ["agent_id"])
    op.create_index("ix_survey_responses_state", "survey_responses", ["state"])
    op.create_index("ix_survey_responses_district", "survey_responses", ["district"])
