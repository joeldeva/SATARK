"""merge legacy response migration revision ids

Revision ID: 0005_merge_legacy_response_revision_ids
Revises: 0004_drop_legacy_survey_responses, 0004_drop_legacy_responses
Create Date: 2026-06-09
"""


revision = "0005_merge_legacy_response_revision_ids"
down_revision = ("0004_drop_legacy_survey_responses", "0004_drop_legacy_responses")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
