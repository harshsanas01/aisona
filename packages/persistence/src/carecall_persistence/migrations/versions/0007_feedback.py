"""feedback: human feedback loop for answers, timeline events, and patterns

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_feedback_id", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("retrieval_version", sa.String(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_feedback_id", name="uq_feedback_external_feedback_id"),
    )
    op.create_index("ix_feedback_external_feedback_id", "feedback", ["external_feedback_id"])
    op.create_index("ix_feedback_target_type", "feedback", ["target_type"])
    op.create_index("ix_feedback_target_id", "feedback", ["target_id"])
    op.create_index("ix_feedback_category", "feedback", ["category"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_category", table_name="feedback")
    op.drop_index("ix_feedback_target_id", table_name="feedback")
    op.drop_index("ix_feedback_target_type", table_name="feedback")
    op.drop_index("ix_feedback_external_feedback_id", table_name="feedback")
    op.drop_table("feedback")
