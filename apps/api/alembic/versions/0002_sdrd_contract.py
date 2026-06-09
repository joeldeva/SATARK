"""sdrd contract: question_graph, version, survey_versions, adaptive_logic, knowledge_sources

Revision ID: 0002_sdrd_contract
Revises: 0001_initial_postgres
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_sdrd_contract"
down_revision = "0001_initial_postgres"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB


def upgrade() -> None:
    # Extend surveys
    op.add_column("surveys", sa.Column("question_graph", JSONB, nullable=True))
    op.add_column(
        "surveys",
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column("surveys", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    # New: survey_versions (publish snapshots)
    op.create_table(
        "survey_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question_graph", JSONB, nullable=False),
        sa.Column("published_by", sa.String(100)),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_survey_versions_survey_id", "survey_versions", ["survey_id"])
    op.create_unique_constraint(
        "uq_survey_versions_survey_version",
        "survey_versions",
        ["survey_id", "version"],
    )

    # New: adaptive_logic (per-survey branches authored in SDRD)
    op.create_table(
        "adaptive_logic",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("survey_id", sa.String(), nullable=False),
        sa.Column("trigger", JSONB, nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("target", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_adaptive_logic_survey_id", "adaptive_logic", ["survey_id"])

    # New: knowledge_sources (admin KB ingest tracking)
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("bucket", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(120)),
        sa.Column("byte_size", sa.Integer()),
        sa.Column("chunk_count", sa.Integer()),
        sa.Column("uploaded_by", sa.String(100)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sha256", sa.String(64)),
    )
    op.create_index("ix_knowledge_sources_bucket", "knowledge_sources", ["bucket"])
    op.create_index("ix_knowledge_sources_sha256", "knowledge_sources", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_sha256", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_bucket", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")

    op.drop_index("ix_adaptive_logic_survey_id", table_name="adaptive_logic")
    op.drop_table("adaptive_logic")

    op.drop_constraint("uq_survey_versions_survey_version", "survey_versions", type_="unique")
    op.drop_index("ix_survey_versions_survey_id", table_name="survey_versions")
    op.drop_table("survey_versions")

    op.drop_column("surveys", "published_at")
    op.drop_column("surveys", "version")
    op.drop_column("surveys", "question_graph")
