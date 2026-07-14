"""person_mentions: people other than the patient referenced in call transcripts

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "person_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_mention_id", sa.String(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("role_label", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("mentioned_name", sa.String(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("extraction_method", sa.String(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False, server_default="unreviewed"),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_mention_id", name="uq_person_mentions_external_mention_id"),
        sa.UniqueConstraint("call_id", "dedupe_key", name="uq_person_mention_call_dedupe_key"),
    )
    op.create_index("ix_person_mentions_external_mention_id", "person_mentions", ["external_mention_id"])
    op.create_index("ix_person_mentions_patient_id", "person_mentions", ["patient_id"])
    op.create_index("ix_person_mentions_relationship_type", "person_mentions", ["relationship_type"])


def downgrade() -> None:
    op.drop_index("ix_person_mentions_relationship_type", table_name="person_mentions")
    op.drop_index("ix_person_mentions_patient_id", table_name="person_mentions")
    op.drop_index("ix_person_mentions_external_mention_id", table_name="person_mentions")
    op.drop_table("person_mentions")
