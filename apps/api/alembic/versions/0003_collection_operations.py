"""collection operations: consents and intelligence sessions

Revision ID: 0003_collection_operations
Revises: 0002_sdrd_contract
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_collection_operations"
down_revision = "0002_sdrd_contract"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "consents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("survey_id", sa.String(80), nullable=False),
        sa.Column("household_id", sa.String(64), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("enumerator_id", sa.String(64), sa.ForeignKey("enumerators.id"), nullable=True),
        sa.Column("consented", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(16)),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_consents_survey_id", "consents", ["survey_id"])
    op.create_index("ix_consents_household_id", "consents", ["household_id"])
    op.create_index("ix_consents_enumerator_id", "consents", ["enumerator_id"])

    op.create_table(
        "intelligence_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("survey_id", sa.String(80), nullable=False),
        sa.Column("household_id", sa.String(64), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("enumerator_id", sa.String(64), sa.ForeignKey("enumerators.id"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_intelligence_sessions_survey_id", "intelligence_sessions", ["survey_id"])
    op.create_index("ix_intelligence_sessions_household_id", "intelligence_sessions", ["household_id"])
    op.create_index("ix_intelligence_sessions_enumerator_id", "intelligence_sessions", ["enumerator_id"])
    op.create_index("ix_intelligence_sessions_status", "intelligence_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_intelligence_sessions_status", table_name="intelligence_sessions")
    op.drop_index("ix_intelligence_sessions_enumerator_id", table_name="intelligence_sessions")
    op.drop_index("ix_intelligence_sessions_household_id", table_name="intelligence_sessions")
    op.drop_index("ix_intelligence_sessions_survey_id", table_name="intelligence_sessions")
    op.drop_table("intelligence_sessions")

    op.drop_index("ix_consents_enumerator_id", table_name="consents")
    op.drop_index("ix_consents_household_id", table_name="consents")
    op.drop_index("ix_consents_survey_id", table_name="consents")
    op.drop_table("consents")
