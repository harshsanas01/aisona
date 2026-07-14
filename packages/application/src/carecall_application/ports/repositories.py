from abc import ABC, abstractmethod
from typing import List, Optional

from carecall_domain import (
    Brief,
    Call,
    Chunk,
    CoordinatorTask,
    Feedback,
    Patient,
    PatientPattern,
    PersonMention,
    QuestionAudit,
    TaskActivity,
    TimelineEvent,
)


class CallRepository(ABC):
    """Port for reading and writing calls. Swappable between an in-memory
    JSON-backed implementation (demo mode) and a PostgreSQL implementation
    (production-like mode) without changing any caller."""

    @abstractmethod
    def list_calls(self) -> List[Call]: ...

    @abstractmethod
    def get_call(self, call_id: str) -> Optional[Call]: ...

    @abstractmethod
    def exists(self, call_id: str) -> bool: ...

    @abstractmethod
    def add_call(self, call: Call) -> None: ...


class PatientRepository(ABC):
    @abstractmethod
    def list_patients(self) -> List[Patient]: ...

    @abstractmethod
    def get_patient(self, patient_id: str) -> Optional[Patient]: ...


class ChunkRepository(ABC):
    """Port over the retrieval-unit store. In memory mode, chunks are derived
    on the fly from calls; in PostgreSQL mode they are durable rows with an
    optional pgvector embedding column."""

    @abstractmethod
    def all_chunks(self) -> List[Chunk]: ...

    @abstractmethod
    def chunks_for_call(self, call_id: str) -> List[Chunk]: ...

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk]) -> None: ...


class TimelineEventRepository(ABC):
    """Port over persisted patient-timeline events. Extraction (deterministic
    or LLM) writes through this port; review-status edits from a coordinator
    (PATCH /api/v1/timeline-events/{event_id}) go through the same port so
    both implementations (in-memory demo mode, PostgreSQL) behave
    identically - see tests/contract for the shared behavioral contract."""

    @abstractmethod
    def list_for_patient(self, patient_id: str) -> List[TimelineEvent]: ...

    @abstractmethod
    def get(self, event_id: str) -> Optional[TimelineEvent]: ...

    @abstractmethod
    def upsert_many(self, events: List[TimelineEvent]) -> None:
        """Insert new events and update existing ones matched by
        (source_call_id, dedupe_key), leaving review_status untouched on an
        already-reviewed event so a rebuild never silently discards a
        coordinator's prior review decision."""
        ...

    @abstractmethod
    def update_review_status(
        self, event_id: str, review_status: str, *, title: Optional[str] = None, description: Optional[str] = None,
    ) -> Optional[TimelineEvent]: ...


class PatternRepository(ABC):
    """Port over persisted patient patterns. Mirrors TimelineEventRepository:
    a rebuild upserts by (patient_id, dedupe_key) and never overwrites a
    pattern a coordinator has already reviewed."""

    @abstractmethod
    def list_for_patient(self, patient_id: str) -> List[PatientPattern]: ...

    @abstractmethod
    def get(self, pattern_id: str) -> Optional[PatientPattern]: ...

    @abstractmethod
    def upsert_many(self, patterns: List[PatientPattern]) -> None: ...

    @abstractmethod
    def update_reviewed_status(self, pattern_id: str, reviewed_status: str) -> Optional[PatientPattern]: ...


class CoordinatorTaskRepository(ABC):
    """Port over persisted coordinator follow-up tasks."""

    @abstractmethod
    def list_tasks(
        self,
        *,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[CoordinatorTask]: ...

    @abstractmethod
    def get(self, task_id: str) -> Optional[CoordinatorTask]: ...

    @abstractmethod
    def find_by_dedupe_key(self, patient_id: str, dedupe_key: str) -> Optional[CoordinatorTask]: ...

    @abstractmethod
    def create(self, task: CoordinatorTask) -> CoordinatorTask: ...

    @abstractmethod
    def update(self, task: CoordinatorTask) -> CoordinatorTask: ...


class TaskActivityRepository(ABC):
    """Port over a task's append-only activity history."""

    @abstractmethod
    def list_for_task(self, task_id: str) -> List[TaskActivity]: ...

    @abstractmethod
    def add(self, activity: TaskActivity) -> None: ...


class BriefRepository(ABC):
    """Port over persisted generated briefs. Unlike timeline events/patterns,
    briefs are not deduped/upserted from a rebuild - each POST /api/v1/briefs
    creates a new brief; only regenerate updates an existing one in place."""

    @abstractmethod
    def create(self, brief: Brief) -> Brief: ...

    @abstractmethod
    def get(self, brief_id: str) -> Optional[Brief]: ...

    @abstractmethod
    def list_briefs(
        self, *, brief_type: Optional[str] = None, patient_id: Optional[str] = None,
    ) -> List[Brief]: ...

    @abstractmethod
    def update(self, brief: Brief) -> Brief: ...


class QuestionAuditRepository(ABC):
    """Port over persisted question-audit records. See QuestionAudit's
    docstring and docs/security/roles-and-privacy.md for the retention
    policy (hash-by-default, full question text never stored)."""

    @abstractmethod
    def create(self, record: QuestionAudit) -> QuestionAudit: ...

    @abstractmethod
    def get(self, request_id: str) -> Optional[QuestionAudit]: ...

    @abstractmethod
    def list_records(
        self, *, answerable: Optional[bool] = None, limit: int = 50,
    ) -> List[QuestionAudit]: ...


class FeedbackRepository(ABC):
    """Port over persisted human feedback (on answers, timeline events, or
    patterns) - an append-only history, never mutated in place."""

    @abstractmethod
    def create(self, feedback: Feedback) -> Feedback: ...

    @abstractmethod
    def get(self, feedback_id: str) -> Optional[Feedback]: ...

    @abstractmethod
    def list_feedback(
        self,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Feedback]: ...


class PersonMentionRepository(ABC):
    """Port over persisted person mentions (people other than the patient
    referenced in a call transcript). Mirrors TimelineEventRepository: a
    rebuild upserts by (source_call_id, dedupe_key) and never overwrites a
    mention a coordinator has already reviewed."""

    @abstractmethod
    def list_for_patient(self, patient_id: str) -> List[PersonMention]: ...

    @abstractmethod
    def get(self, mention_id: str) -> Optional[PersonMention]: ...

    @abstractmethod
    def upsert_many(self, mentions: List[PersonMention]) -> None: ...

    @abstractmethod
    def update_review_status(
        self,
        mention_id: str,
        review_status: str,
        *,
        corrected_relationship_type: Optional[str] = None,
        corrected_name: Optional[str] = None,
    ) -> Optional[PersonMention]: ...
