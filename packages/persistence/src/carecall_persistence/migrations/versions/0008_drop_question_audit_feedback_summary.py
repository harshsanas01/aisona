"""drop question_audit.feedback_summary - now computed live from feedback records

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("question_audit", "feedback_summary")


def downgrade() -> None:
    op.add_column(
        "question_audit",
        sa.Column("feedback_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
