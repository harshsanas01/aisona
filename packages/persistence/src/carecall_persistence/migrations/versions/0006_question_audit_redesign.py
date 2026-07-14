"""question_audit redesign: full audit trail, hash-by-default retention

The original question_audit table (from 0001) was scaffolded but never
written to by the application, and stored the full question text - which
does not match the privacy model this feature needs (hash-by-default,
question text only retained as an explicitly-opted-in, truncated preview).
This migration replaces it outright rather than layering ALTER TABLEs on
top of a table nothing has ever populated.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("question_audit")

    op.create_table(
        "question_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_request_id", sa.String(), nullable=False),
        sa.Column("question_hash", sa.String(), nullable=False),
        sa.Column("question_preview", sa.String(), nullable=True),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("storage_mode", sa.String(), nullable=False),
        sa.Column("retrieval_mode", sa.String(), nullable=False),
        sa.Column("lexical_weight", sa.Float(), nullable=False),
        sa.Column("semantic_weight", sa.Float(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("relevance_threshold", sa.Float(), nullable=False),
        sa.Column("candidate_chunk_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("selected_evidence_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("answer_mode", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("token_usage", postgresql.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("answerable", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("final_citation_call_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("grounding_checks", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_category", sa.String(), nullable=True),
        sa.Column("feedback_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_request_id", name="uq_question_audit_external_request_id"),
    )
    op.create_index("ix_question_audit_external_request_id", "question_audit", ["external_request_id"])
    op.create_index("ix_question_audit_question_hash", "question_audit", ["question_hash"])
    op.create_index("ix_question_audit_answerable", "question_audit", ["answerable"])
    op.create_index("ix_question_audit_created_at", "question_audit", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_question_audit_created_at", table_name="question_audit")
    op.drop_index("ix_question_audit_answerable", table_name="question_audit")
    op.drop_index("ix_question_audit_question_hash", table_name="question_audit")
    op.drop_index("ix_question_audit_external_request_id", table_name="question_audit")
    op.drop_table("question_audit")

    op.create_table(
        "question_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("answerable", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("cited_call_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("retrieval_mode", sa.String(), nullable=False),
        sa.Column("answer_mode", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
