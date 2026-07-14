"""patient_patterns: longitudinal pattern/trend detection

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_pattern_id", sa.String(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("first_observed_date", sa.String(), nullable=False),
        sa.Column("latest_observed_date", sa.String(), nullable=False),
        sa.Column("related_timeline_event_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("related_call_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("detector_version", sa.String(), nullable=False),
        sa.Column("reviewed_status", sa.String(), nullable=False, server_default="unreviewed"),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_pattern_id", name="uq_patient_patterns_external_pattern_id"),
        sa.UniqueConstraint("patient_id", "dedupe_key", name="uq_pattern_patient_dedupe_key"),
    )
    op.create_index("ix_patient_patterns_external_pattern_id", "patient_patterns", ["external_pattern_id"])
    op.create_index("ix_patient_patterns_patient_id", "patient_patterns", ["patient_id"])
    op.create_index("ix_patient_patterns_status", "patient_patterns", ["status"])


def downgrade() -> None:
    op.drop_index("ix_patient_patterns_status", table_name="patient_patterns")
    op.drop_index("ix_patient_patterns_patient_id", table_name="patient_patterns")
    op.drop_index("ix_patient_patterns_external_pattern_id", table_name="patient_patterns")
    op.drop_table("patient_patterns")
