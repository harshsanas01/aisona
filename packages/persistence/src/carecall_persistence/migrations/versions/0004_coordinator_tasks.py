"""coordinator_tasks, task_activity: care coordinator action center

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coordinator_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_task_id", sa.String(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("is_suggested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("source_call_id", sa.String(), nullable=True),
        sa.Column("source_turn_start", sa.Integer(), nullable=True),
        sa.Column("source_turn_end", sa.Integer(), nullable=True),
        sa.Column("assignee", sa.String(), nullable=True),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_task_id", name="uq_coordinator_tasks_external_task_id"),
        sa.UniqueConstraint("patient_id", "dedupe_key", name="uq_task_patient_dedupe_key"),
    )
    op.create_index("ix_coordinator_tasks_external_task_id", "coordinator_tasks", ["external_task_id"])
    op.create_index("ix_coordinator_tasks_patient_id", "coordinator_tasks", ["patient_id"])
    op.create_index("ix_coordinator_tasks_status", "coordinator_tasks", ["status"])
    op.create_index("ix_coordinator_tasks_due_date", "coordinator_tasks", ["due_date"])

    op.create_table(
        "task_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_activity_id", sa.String(), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coordinator_tasks.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=True),
        sa.Column("to_status", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_activity_id", name="uq_task_activity_external_activity_id"),
    )
    op.create_index("ix_task_activity_external_activity_id", "task_activity", ["external_activity_id"])
    op.create_index("ix_task_activity_task_id", "task_activity", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_activity_task_id", table_name="task_activity")
    op.drop_index("ix_task_activity_external_activity_id", table_name="task_activity")
    op.drop_table("task_activity")

    op.drop_index("ix_coordinator_tasks_due_date", table_name="coordinator_tasks")
    op.drop_index("ix_coordinator_tasks_status", table_name="coordinator_tasks")
    op.drop_index("ix_coordinator_tasks_patient_id", table_name="coordinator_tasks")
    op.drop_index("ix_coordinator_tasks_external_task_id", table_name="coordinator_tasks")
    op.drop_table("coordinator_tasks")
