"""briefs: daily/weekly operational care briefs

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_brief_id", sa.String(), nullable=False),
        sa.Column("brief_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.String(), nullable=False),
        sa.Column("end_date", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=True),
        sa.Column("include_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bullets", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_brief_id", name="uq_briefs_external_brief_id"),
    )
    op.create_index("ix_briefs_external_brief_id", "briefs", ["external_brief_id"])
    op.create_index("ix_briefs_brief_type", "briefs", ["brief_type"])
    op.create_index("ix_briefs_patient_id", "briefs", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_briefs_patient_id", table_name="briefs")
    op.drop_index("ix_briefs_brief_type", table_name="briefs")
    op.drop_index("ix_briefs_external_brief_id", table_name="briefs")
    op.drop_table("briefs")
