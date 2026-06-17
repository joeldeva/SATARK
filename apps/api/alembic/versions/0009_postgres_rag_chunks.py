"""postgres-backed RAG chunks

Revision ID: 0009_postgres_rag_chunks
Revises: 0008_validation_result_confidence
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_postgres_rag_chunks"
down_revision = "0008_validation_result_confidence"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "rag_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("bucket", sa.String(64), nullable=False),
        sa.Column("chunk_id", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", JSON_DOCUMENT, nullable=False),
        sa.Column("metadata_json", JSON_DOCUMENT, nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("bucket", "chunk_id", name="uq_rag_chunks_bucket_chunk_id"),
    )
    op.create_index("ix_rag_chunks_bucket", "rag_chunks", ["bucket"])
    op.create_index("ix_rag_chunks_source_id", "rag_chunks", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_source_id", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_bucket", table_name="rag_chunks")
    op.drop_table("rag_chunks")
