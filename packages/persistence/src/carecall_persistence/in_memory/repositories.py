from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, List, Optional

from carecall_application.ports.repositories import (
    BriefRepository,
    CallRepository,
    ChunkRepository,
    CoordinatorTaskRepository,
    FeedbackRepository,
    PatientRepository,
    PatternRepository,
    PersonMentionRepository,
    QuestionAuditRepository,
    TaskActivityRepository,
    TimelineEventRepository,
)
from carecall_domain import (
    Brief,
    Call,
    Chunk,
    CoordinatorTask,
    DuplicateCallError,
    Feedback,
    Patient,
    PatientPattern,
    PersonMention,
    QuestionAudit,
    TaskActivity,
    TimelineEvent,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryCallRepository(CallRepository):
    def __init__(self, calls: Optional[List[Call]] = None):
        self._calls: Dict[str, Call] = {}
        self._order: List[str] = []
        for call in calls or []:
            self.add_call(call)

    def list_calls(self) -> List[Call]:
        return [self._calls[call_id] for call_id in self._order]

    def get_call(self, call_id: str) -> Optional[Call]:
        return self._calls.get(call_id)

    def exists(self, call_id: str) -> bool:
        return call_id in self._calls

    def add_call(self, call: Call) -> None:
        if call.call_id in self._calls:
            raise DuplicateCallError(f"Call {call.call_id} already exists")
        self._calls[call.call_id] = call
        self._order.append(call.call_id)


class InMemoryPatientRepository(PatientRepository):
    """Patients only exist attached to calls in demo mode - there is no
    standalone patient fixture. Reads live from the CallRepository (rather
    than keeping its own snapshot) so a patient introduced by a newly
    ingested call shows up immediately, matching PostgresPatientRepository's
    behavior of always querying current state."""

    def __init__(self, call_repository: CallRepository):
        self._call_repository = call_repository

    def list_patients(self) -> List[Patient]:
        seen: Dict[str, Patient] = {}
        for call in self._call_repository.list_calls():
            seen.setdefault(call.patient.id, call.patient)
        return list(seen.values())

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        for call in self._call_repository.list_calls():
            if call.patient.id == patient_id:
                return call.patient
        return None


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self, chunks: Optional[List[Chunk]] = None):
        self._chunks: List[Chunk] = []
        self._by_call: Dict[str, List[Chunk]] = {}
        if chunks:
            self.add_chunks(chunks)

    def all_chunks(self) -> List[Chunk]:
        return list(self._chunks)

    def chunks_for_call(self, call_id: str) -> List[Chunk]:
        return list(self._by_call.get(call_id, []))

    def add_chunks(self, chunks: List[Chunk]) -> None:
        for chunk in chunks:
            self._chunks.append(chunk)
            self._by_call.setdefault(chunk.call_id, []).append(chunk)


class InMemoryTimelineEventRepository(TimelineEventRepository):
    def __init__(self, events: Optional[List[TimelineEvent]] = None):
        self._events: Dict[str, TimelineEvent] = {}
        self._order: List[str] = []
        self.upsert_many(events or [])

    def list_for_patient(self, patient_id: str) -> List[TimelineEvent]:
        return [
            self._events[event_id] for event_id in self._order
            if self._events[event_id].patient_id == patient_id
        ]

    def get(self, event_id: str) -> Optional[TimelineEvent]:
        return self._events.get(event_id)

    def upsert_many(self, events: List[TimelineEvent]) -> None:
        for event in events:
            existing_id = self._match_existing(event)
            if existing_id is None:
                self._events[event.event_id] = event
                self._order.append(event.event_id)
                continue
            existing = self._events[existing_id]
            if existing.review_status != "unreviewed":
                continue  # a coordinator's prior review decision always wins over a rebuild
            self._events[existing_id] = replace(event, event_id=existing_id)

    def update_review_status(
        self, event_id: str, review_status: str, *, title: Optional[str] = None, description: Optional[str] = None,
    ) -> Optional[TimelineEvent]:
        existing = self._events.get(event_id)
        if existing is None:
            return None
        updated = replace(
            existing,
            review_status=review_status,
            title=title if title is not None else existing.title,
            description=description if description is not None else existing.description,
            updated_at=_utcnow_iso(),
        )
        self._events[event_id] = updated
        return updated

    def _match_existing(self, event: TimelineEvent) -> Optional[str]:
        if event.dedupe_key is None:
            return event.event_id if event.event_id in self._events else None
        for existing_id in self._order:
            existing = self._events[existing_id]
            if existing.source_call_id == event.source_call_id and existing.dedupe_key == event.dedupe_key:
                return existing_id
        return None


class InMemoryPatternRepository(PatternRepository):
    def __init__(self, patterns: Optional[List[PatientPattern]] = None):
        self._patterns: Dict[str, PatientPattern] = {}
        self._order: List[str] = []
        self.upsert_many(patterns or [])

    def list_for_patient(self, patient_id: str) -> List[PatientPattern]:
        return [
            self._patterns[pattern_id] for pattern_id in self._order
            if self._patterns[pattern_id].patient_id == patient_id
        ]

    def get(self, pattern_id: str) -> Optional[PatientPattern]:
        return self._patterns.get(pattern_id)

    def upsert_many(self, patterns: List[PatientPattern]) -> None:
        for pattern in patterns:
            existing_id = self._match_existing(pattern)
            if existing_id is None:
                self._patterns[pattern.pattern_id] = pattern
                self._order.append(pattern.pattern_id)
                continue
            existing = self._patterns[existing_id]
            if existing.reviewed_status != "unreviewed":
                continue  # a coordinator's prior review decision always wins over a rebuild
            self._patterns[existing_id] = replace(pattern, pattern_id=existing_id)

    def update_reviewed_status(self, pattern_id: str, reviewed_status: str) -> Optional[PatientPattern]:
        existing = self._patterns.get(pattern_id)
        if existing is None:
            return None
        updated = replace(existing, reviewed_status=reviewed_status, updated_at=_utcnow_iso())
        self._patterns[pattern_id] = updated
        return updated

    def _match_existing(self, pattern: PatientPattern) -> Optional[str]:
        if not pattern.dedupe_key:
            return pattern.pattern_id if pattern.pattern_id in self._patterns else None
        for existing_id in self._order:
            existing = self._patterns[existing_id]
            if existing.patient_id == pattern.patient_id and existing.dedupe_key == pattern.dedupe_key:
                return existing_id
        return None


class InMemoryCoordinatorTaskRepository(CoordinatorTaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[str, CoordinatorTask] = {}
        self._order: List[str] = []

    def list_tasks(
        self,
        *,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[CoordinatorTask]:
        tasks = [self._tasks[task_id] for task_id in self._order]
        if patient_id:
            tasks = [t for t in tasks if t.patient_id == patient_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if category:
            tasks = [t for t in tasks if t.category == category]
        if assignee:
            tasks = [t for t in tasks if t.assignee == assignee]
        return tasks

    def get(self, task_id: str) -> Optional[CoordinatorTask]:
        return self._tasks.get(task_id)

    def find_by_dedupe_key(self, patient_id: str, dedupe_key: str) -> Optional[CoordinatorTask]:
        for task in self._tasks.values():
            if task.patient_id == patient_id and task.dedupe_key == dedupe_key:
                return task
        return None

    def create(self, task: CoordinatorTask) -> CoordinatorTask:
        self._tasks[task.task_id] = task
        self._order.append(task.task_id)
        return task

    def update(self, task: CoordinatorTask) -> CoordinatorTask:
        self._tasks[task.task_id] = task
        return task


class InMemoryTaskActivityRepository(TaskActivityRepository):
    def __init__(self) -> None:
        self._activities: Dict[str, List[TaskActivity]] = {}

    def list_for_task(self, task_id: str) -> List[TaskActivity]:
        return list(self._activities.get(task_id, []))

    def add(self, activity: TaskActivity) -> None:
        self._activities.setdefault(activity.task_id, []).append(activity)


class InMemoryBriefRepository(BriefRepository):
    def __init__(self) -> None:
        self._briefs: Dict[str, Brief] = {}
        self._order: List[str] = []

    def create(self, brief: Brief) -> Brief:
        self._briefs[brief.brief_id] = brief
        self._order.append(brief.brief_id)
        return brief

    def get(self, brief_id: str) -> Optional[Brief]:
        return self._briefs.get(brief_id)

    def list_briefs(
        self, *, brief_type: Optional[str] = None, patient_id: Optional[str] = None,
    ) -> List[Brief]:
        briefs = [self._briefs[bid] for bid in self._order]
        if brief_type:
            briefs = [b for b in briefs if b.brief_type == brief_type]
        if patient_id:
            briefs = [b for b in briefs if b.patient_id == patient_id]
        return briefs

    def update(self, brief: Brief) -> Brief:
        self._briefs[brief.brief_id] = brief
        return brief


class InMemoryQuestionAuditRepository(QuestionAuditRepository):
    def __init__(self) -> None:
        self._records: Dict[str, QuestionAudit] = {}
        self._order: List[str] = []

    def create(self, record: QuestionAudit) -> QuestionAudit:
        self._records[record.request_id] = record
        self._order.append(record.request_id)
        return record

    def get(self, request_id: str) -> Optional[QuestionAudit]:
        return self._records.get(request_id)

    def list_records(self, *, answerable: Optional[bool] = None, limit: int = 50) -> List[QuestionAudit]:
        records = [self._records[rid] for rid in reversed(self._order)]
        if answerable is not None:
            records = [r for r in records if r.answerable == answerable]
        return records[:limit]


class InMemoryFeedbackRepository(FeedbackRepository):
    def __init__(self) -> None:
        self._feedback: Dict[str, Feedback] = {}
        self._order: List[str] = []

    def create(self, feedback: Feedback) -> Feedback:
        self._feedback[feedback.feedback_id] = feedback
        self._order.append(feedback.feedback_id)
        return feedback

    def get(self, feedback_id: str) -> Optional[Feedback]:
        return self._feedback.get(feedback_id)

    def list_feedback(
        self,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Feedback]:
        records = [self._feedback[fid] for fid in reversed(self._order)]
        if target_type:
            records = [r for r in records if r.target_type == target_type]
        if target_id:
            records = [r for r in records if r.target_id == target_id]
        if category:
            records = [r for r in records if r.category == category]
        return records[:limit]


class InMemoryPersonMentionRepository(PersonMentionRepository):
    def __init__(self, mentions: Optional[List[PersonMention]] = None):
        self._mentions: Dict[str, PersonMention] = {}
        self._order: List[str] = []
        self.upsert_many(mentions or [])

    def list_for_patient(self, patient_id: str) -> List[PersonMention]:
        return [
            self._mentions[mention_id] for mention_id in self._order
            if self._mentions[mention_id].patient_id == patient_id
        ]

    def get(self, mention_id: str) -> Optional[PersonMention]:
        return self._mentions.get(mention_id)

    def upsert_many(self, mentions: List[PersonMention]) -> None:
        for mention in mentions:
            existing_id = self._match_existing(mention)
            if existing_id is None:
                self._mentions[mention.mention_id] = mention
                self._order.append(mention.mention_id)
                continue
            existing = self._mentions[existing_id]
            if existing.review_status != "unreviewed":
                continue  # a coordinator's prior review decision always wins over a rebuild
            self._mentions[existing_id] = replace(mention, mention_id=existing_id)

    def update_review_status(
        self,
        mention_id: str,
        review_status: str,
        *,
        corrected_relationship_type: Optional[str] = None,
        corrected_name: Optional[str] = None,
    ) -> Optional[PersonMention]:
        existing = self._mentions.get(mention_id)
        if existing is None:
            return None
        updated = replace(
            existing,
            review_status=review_status,
            relationship_type=(
                corrected_relationship_type if corrected_relationship_type is not None else existing.relationship_type
            ),
            mentioned_name=corrected_name if corrected_name is not None else existing.mentioned_name,
            updated_at=_utcnow_iso(),
        )
        self._mentions[mention_id] = updated
        return updated

    def _match_existing(self, mention: PersonMention) -> Optional[str]:
        if mention.dedupe_key is None:
            return mention.mention_id if mention.mention_id in self._mentions else None
        for existing_id in self._order:
            existing = self._mentions[existing_id]
            if existing.source_call_id == mention.source_call_id and existing.dedupe_key == mention.dedupe_key:
                return existing_id
        return None
