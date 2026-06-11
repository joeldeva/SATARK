"""add metadata columns to classification_codes

Revision ID: 0006_classification_code_metadata
Revises: 0005_merge_legacy_response_revision_ids
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_classification_code_metadata"
down_revision = "0005_merge_legacy_response_revision_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("classification_codes", sa.Column("family", sa.String(255), nullable=True))
    op.add_column("classification_codes", sa.Column("sector", sa.String(255), nullable=True))
    op.add_column("classification_codes", sa.Column("level", sa.String(24), nullable=True))
    op.add_column("classification_codes", sa.Column("section", sa.String(24), nullable=True))
    op.add_column("classification_codes", sa.Column("parent_code", sa.String(32), nullable=True))
    op.create_index("ix_classification_codes_sector", "classification_codes", ["sector"])
    op.create_index("ix_classification_codes_section", "classification_codes", ["section"])
    op.create_index("ix_classification_codes_parent_code", "classification_codes", ["parent_code"])


def downgrade() -> None:
    op.drop_index("ix_classification_codes_parent_code", table_name="classification_codes")
    op.drop_index("ix_classification_codes_section", table_name="classification_codes")
    op.drop_index("ix_classification_codes_sector", table_name="classification_codes")
    op.drop_column("classification_codes", "parent_code")
    op.drop_column("classification_codes", "section")
    op.drop_column("classification_codes", "level")
    op.drop_column("classification_codes", "sector")
    op.drop_column("classification_codes", "family")
