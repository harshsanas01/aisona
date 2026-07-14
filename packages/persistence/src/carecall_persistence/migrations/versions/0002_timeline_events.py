"""timeline_events: patient longitudinal timeline

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_event_id", sa.String(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("observed_date", sa.String(), nullable=False),
        sa.Column("turn_start", sa.Integer(), nullable=False),
        sa.Column("turn_end", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("extraction_method", sa.String(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False, server_default="unreviewed"),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_event_id", name="uq_timeline_events_external_event_id"),
        sa.UniqueConstraint("call_id", "dedupe_key", name="uq_timeline_event_call_dedupe_key"),
    )
    op.create_index("ix_timeline_events_external_event_id", "timeline_events", ["external_event_id"])
    op.create_index("ix_timeline_events_patient_id", "timeline_events", ["patient_id"])
    op.create_index("ix_timeline_events_observed_date", "timeline_events", ["observed_date"])


def downgrade() -> None:
    op.drop_index("ix_timeline_events_observed_date", table_name="timeline_events")
    op.drop_index("ix_timeline_events_patient_id", table_name="timeline_events")
    op.drop_index("ix_timeline_events_external_event_id", table_name="timeline_events")
    op.drop_table("timeline_events")
