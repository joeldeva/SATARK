"""hash-chained responses + mock identity registry

Revision ID: 0007_hash_chain_and_mock_identities
Revises: 0006_classification_code_metadata
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_hash_chain_and_mock_identities"
down_revision = "0006_classification_code_metadata"
branch_labels = None
depends_on = None

JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # Tamper-evident hash chain on responses.
    op.add_column("responses", sa.Column("content_hash", sa.Text(), nullable=False, server_default=""))
    op.add_column("responses", sa.Column("prev_hash", sa.Text(), nullable=True))
    op.add_column("responses", sa.Column("chain_index", sa.BigInteger(), nullable=True))
    op.create_index("ix_responses_chain_index", "responses", ["chain_index"])

    # Mock government-ID registry (DEMO ONLY — no real Aadhaar/UIDAI integration).
    op.create_table(
        "mock_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("id_type", sa.String(24), nullable=False),
        sa.Column("id_number", sa.String(40), nullable=False),
        sa.Column("last4", sa.String(8), nullable=False),
        sa.Column("name", sa.String(120)),
        sa.Column("district", sa.String(120)),
        sa.Column("village", sa.String(120)),
        sa.Column("lgd_code", sa.String(40)),
        sa.Column("household_size", sa.Integer()),
        sa.Column("last_occupation", sa.String(80)),
        sa.Column("record", JSON_DOCUMENT, nullable=False, server_default="{}"),
    )
    op.create_index("ix_mock_identities_id_type", "mock_identities", ["id_type"])
    op.create_index("ix_mock_identities_last4", "mock_identities", ["last4"])


def downgrade() -> None:
    op.drop_index("ix_mock_identities_last4", table_name="mock_identities")
    op.drop_index("ix_mock_identities_id_type", table_name="mock_identities")
    op.drop_table("mock_identities")
    op.drop_index("ix_responses_chain_index", table_name="responses")
    op.drop_column("responses", "chain_index")
    op.drop_column("responses", "prev_hash")
    op.drop_column("responses", "content_hash")
