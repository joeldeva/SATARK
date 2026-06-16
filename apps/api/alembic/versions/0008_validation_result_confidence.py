"""per-method confidence on validation_results

Revision ID: 0008_validation_result_confidence
Revises: 0007_hash_chain_and_mock_identities
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_validation_result_confidence"
down_revision = "0007_hash_chain_and_mock_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_results", sa.Column("confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("validation_results", "confidence")
