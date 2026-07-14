import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# text-embedding-3-small produces 1536-dim vectors; kept as a constant so a
# migration can be written if a different embedding model's dimension is
# adopted later.
EMBEDDING_DIM = 1536


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PatientRow(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_patient_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    calls: Mapped[List["CallRow"]] = relationship(back_populates="patient")


class CallRow(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_call_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    call_date: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="fixture")
    ingestion_status: Mapped[str] = mapped_column(String, nullable=False, default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["PatientRow"] = relationship(back_populates="calls")
    turns: Mapped[List["TranscriptTurnRow"]] = relationship(
        back_populates="call", order_by="TranscriptTurnRow.turn_number", cascade="all, delete-orphan",
    )
    chunks: Mapped[List["TranscriptChunkRow"]] = relationship(back_populates="call", cascade="all, delete-orphan")


class TranscriptTurnRow(Base):
    __tablename__ = "transcript_turns"
    __table_args__ = (UniqueConstraint("call_id", "turn_number", name="uq_turn_call_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    call: Mapped["CallRow"] = relationship(back_populates="turns")


class TranscriptChunkRow(Base):
    __tablename__ = "transcript_chunks"
    __table_args__ = (UniqueConstraint("call_id", "content_hash", name="uq_chunk_call_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    turn_start: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_end: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    call: Mapped["CallRow"] = relationship(back_populates="chunks")


class IngestionJobRow(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class QuestionAuditRow(Base):
    """Full audit record for one /api/ask request. question_preview is
    nullable and only ever populated when retention is explicitly enabled
    (CARECALL_AUDIT_RETAIN_QUESTION_PREVIEW) - the full question text is
    never stored, only a hash plus (optionally) a short truncated preview.
    See docs/security/roles-and-privacy.md."""

    __tablename__ = "question_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_request_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    question_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    question_preview: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    storage_mode: Mapped[str] = mapped_column(String, nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(String, nullable=False)
    lexical_weight: Mapped[float] = mapped_column(nullable=False)
    semantic_weight: Mapped[float] = mapped_column(nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    relevance_threshold: Mapped[float] = mapped_column(nullable=False)
    candidate_chunk_ids: Mapped[list] = mapped_column(JSONB, default=list)
    selected_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)
    answer_mode: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    token_usage: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[float] = mapped_column(nullable=False)
    answerable: Mapped[bool] = mapped_column(nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    final_citation_call_ids: Mapped[list] = mapped_column(JSONB, default=list)
    grounding_checks: Mapped[dict] = mapped_column(JSONB, default=dict)
    fallback_used: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class TimelineEventRow(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (UniqueConstraint("call_id", "dedupe_key", name="uq_timeline_event_call_dedupe_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    observed_date: Mapped[str] = mapped_column(String, nullable=False, index=True)
    turn_start: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_end: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String, nullable=False)
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="unreviewed")
    dedupe_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["PatientRow"] = relationship()
    call: Mapped["CallRow"] = relationship()


class PatternRow(Base):
    __tablename__ = "patient_patterns"
    __table_args__ = (UniqueConstraint("patient_id", "dedupe_key", name="uq_pattern_patient_dedupe_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_pattern_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    first_observed_date: Mapped[str] = mapped_column(String, nullable=False)
    latest_observed_date: Mapped[str] = mapped_column(String, nullable=False)
    related_timeline_event_ids: Mapped[list] = mapped_column(JSONB, default=list)
    related_call_ids: Mapped[list] = mapped_column(JSONB, default=list)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    detector_version: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_status: Mapped[str] = mapped_column(String, nullable=False, default="unreviewed")
    dedupe_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["PatientRow"] = relationship()


class CoordinatorTaskRow(Base):
    __tablename__ = "coordinator_tasks"
    __table_args__ = (UniqueConstraint("patient_id", "dedupe_key", name="uq_task_patient_dedupe_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_task_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    is_suggested: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    source_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_turn_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_turn_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assignee: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["PatientRow"] = relationship()


class TaskActivityRow(Base):
    __tablename__ = "task_activity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_activity_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coordinator_tasks.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    task: Mapped["CoordinatorTaskRow"] = relationship()


class BriefRow(Base):
    __tablename__ = "briefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_brief_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    brief_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    start_date: Mapped[str] = mapped_column(String, nullable=False)
    end_date: Mapped[str] = mapped_column(String, nullable=False)
    # Plain external patient id, not a FK - a center-wide brief's bullets span
    # many patients (denormalized onto each bullet), so this column is only
    # ever used to filter for a single patient's briefs, never joined.
    patient_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    include_resolved: Mapped[bool] = mapped_column(nullable=False, default=False)
    bullets: Mapped[list] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_feedback_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieval_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class PersonMentionRow(Base):
    __tablename__ = "person_mentions"
    __table_args__ = (UniqueConstraint("call_id", "dedupe_key", name="uq_person_mention_call_dedupe_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_mention_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    role_label: Mapped[str] = mapped_column(String, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    mentioned_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String, nullable=False)
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="unreviewed")
    dedupe_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["PatientRow"] = relationship()
    call: Mapped["CallRow"] = relationship()
