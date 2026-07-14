import hashlib
from datetime import datetime
from typing import List, Optional

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
    BriefBullet,
    Call,
    Chunk,
    CoordinatorTask,
    DuplicateCallError,
    Feedback,
    Patient,
    PatientPattern,
    PatternEvidenceRef,
    PersonMention,
    QuestionAudit,
    TaskActivity,
    TimelineEvent,
    Turn,
)
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from .models import (
    BriefRow,
    CallRow,
    CoordinatorTaskRow,
    FeedbackRow,
    PatientRow,
    PatternRow,
    PersonMentionRow,
    QuestionAuditRow,
    TaskActivityRow,
    TimelineEventRow,
    TranscriptChunkRow,
    TranscriptTurnRow,
)


class PostgresPatientRepository(PatientRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_patients(self) -> List[Patient]:
        with self._session_factory() as session:
            rows = session.execute(select(PatientRow)).scalars().all()
            return [Patient(id=row.external_patient_id, name=row.name, age=row.age) for row in rows]

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        with self._session_factory() as session:
            row = session.execute(
                select(PatientRow).where(PatientRow.external_patient_id == patient_id)
            ).scalar_one_or_none()
            return Patient(id=row.external_patient_id, name=row.name, age=row.age) if row else None


class PostgresCallRepository(CallRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_calls(self) -> List[Call]:
        with self._session_factory() as session:
            rows = session.execute(select(CallRow).order_by(CallRow.call_date)).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get_call(self, call_id: str) -> Optional[Call]:
        with self._session_factory() as session:
            row = session.execute(
                select(CallRow).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def exists(self, call_id: str) -> bool:
        with self._session_factory() as session:
            row_id = session.execute(
                select(CallRow.id).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            return row_id is not None

    def add_call(self, call: Call) -> None:
        """Idempotent on external_call_id: raises DuplicateCallError instead
        of silently duplicating a re-ingested call. Runs as a single
        transaction - patient upsert, call row, and every turn row commit
        together or not at all."""
        with self._session_factory() as session:
            existing = session.execute(
                select(CallRow.id).where(CallRow.external_call_id == call.call_id)
            ).scalar_one_or_none()
            if existing is not None:
                raise DuplicateCallError(f"Call {call.call_id} already exists")

            patient_row = session.execute(
                select(PatientRow).where(PatientRow.external_patient_id == call.patient.id)
            ).scalar_one_or_none()
            if patient_row is None:
                patient_row = PatientRow(
                    external_patient_id=call.patient.id, name=call.patient.name, age=call.patient.age,
                )
                session.add(patient_row)
                session.flush()

            call_row = CallRow(
                external_call_id=call.call_id,
                patient_id=patient_row.id,
                call_date=call.date,
                duration_seconds=call.duration_seconds,
            )
            session.add(call_row)
            session.flush()

            for index, turn in enumerate(call.turns, start=1):
                session.add(TranscriptTurnRow(
                    call_id=call_row.id, turn_number=index, speaker=turn.speaker, text=turn.text,
                ))
            session.commit()

    @staticmethod
    def _to_domain(row: CallRow) -> Call:
        turns = [Turn(speaker=t.speaker, text=t.text) for t in sorted(row.turns, key=lambda t: t.turn_number)]
        patient = Patient(id=row.patient.external_patient_id, name=row.patient.name, age=row.patient.age)
        return Call(
            call_id=row.external_call_id,
            date=row.call_date,
            patient=patient,
            duration_seconds=row.duration_seconds,
            turns=turns,
        )


class PostgresChunkRepository(ChunkRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def all_chunks(self) -> List[Chunk]:
        with self._session_factory() as session:
            rows = session.execute(select(TranscriptChunkRow)).scalars().all()
            return [self._to_domain(row) for row in rows]

    def chunks_for_call(self, call_id: str) -> List[Chunk]:
        with self._session_factory() as session:
            call_row = session.execute(
                select(CallRow).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            if call_row is None:
                return []
            rows = session.execute(
                select(TranscriptChunkRow).where(TranscriptChunkRow.call_id == call_row.id)
            ).scalars().all()
            return [self._to_domain(row, call_row=call_row) for row in rows]

    def add_chunks(self, chunks: List[Chunk]) -> None:
        with self._session_factory() as session:
            for chunk in chunks:
                call_row = session.execute(
                    select(CallRow).where(CallRow.external_call_id == chunk.call_id)
                ).scalar_one_or_none()
                if call_row is None:
                    continue
                content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
                session.add(TranscriptChunkRow(
                    call_id=call_row.id,
                    turn_start=chunk.turn_start,
                    turn_end=chunk.turn_end,
                    text=chunk.text,
                    content_hash=content_hash,
                ))
            session.commit()

    @staticmethod
    def _to_domain(row: TranscriptChunkRow, call_row: Optional[CallRow] = None) -> Chunk:
        call_row = call_row or row.call
        patient = call_row.patient
        turns = [
            Turn(speaker=t.speaker, text=t.text)
            for t in sorted(call_row.turns, key=lambda t: t.turn_number)
            if row.turn_start <= t.turn_number <= row.turn_end
        ]
        metadata_text = " ".join([
            patient.name, patient.external_patient_id, call_row.call_date, call_row.external_call_id,
            " ".join(t.text for t in turns),
        ])
        return Chunk(
            chunk_id=f"{call_row.external_call_id}:{row.turn_start}:{row.turn_end}",
            call_id=call_row.external_call_id,
            patient_id=patient.external_patient_id,
            patient_name=patient.name,
            date=call_row.call_date,
            turn_start=row.turn_start,
            turn_end=row.turn_end,
            turns=turns,
            metadata_text=metadata_text,
            text=row.text,
        )


class PostgresTimelineEventRepository(TimelineEventRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_for_patient(self, patient_id: str) -> List[TimelineEvent]:
        with self._session_factory() as session:
            rows = session.execute(
                select(TimelineEventRow)
                .join(PatientRow, TimelineEventRow.patient_id == PatientRow.id)
                .where(PatientRow.external_patient_id == patient_id)
                .order_by(TimelineEventRow.observed_date)
            ).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get(self, event_id: str) -> Optional[TimelineEvent]:
        with self._session_factory() as session:
            row = session.execute(
                select(TimelineEventRow).where(TimelineEventRow.external_event_id == event_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def upsert_many(self, events: List[TimelineEvent]) -> None:
        with self._session_factory() as session:
            for event in events:
                patient_row = session.execute(
                    select(PatientRow).where(PatientRow.external_patient_id == event.patient_id)
                ).scalar_one_or_none()
                call_row = session.execute(
                    select(CallRow).where(CallRow.external_call_id == event.source_call_id)
                ).scalar_one_or_none()
                if patient_row is None or call_row is None:
                    continue

                existing = None
                if event.dedupe_key is not None:
                    existing = session.execute(
                        select(TimelineEventRow).where(
                            TimelineEventRow.call_id == call_row.id,
                            TimelineEventRow.dedupe_key == event.dedupe_key,
                        )
                    ).scalar_one_or_none()

                if existing is None:
                    session.add(TimelineEventRow(
                        external_event_id=event.event_id,
                        patient_id=patient_row.id,
                        call_id=call_row.id,
                        event_type=event.event_type,
                        title=event.title,
                        description=event.description,
                        observed_date=event.observed_date,
                        turn_start=event.source_turn_start,
                        turn_end=event.source_turn_end,
                        quote=event.quote,
                        confidence=event.confidence,
                        extraction_method=event.extraction_method,
                        review_status=event.review_status,
                        dedupe_key=event.dedupe_key,
                    ))
                elif existing.review_status == "unreviewed":
                    # A coordinator's prior review decision always wins over a rebuild.
                    existing.event_type = event.event_type
                    existing.title = event.title
                    existing.description = event.description
                    existing.observed_date = event.observed_date
                    existing.turn_start = event.source_turn_start
                    existing.turn_end = event.source_turn_end
                    existing.quote = event.quote
                    existing.confidence = event.confidence
                    existing.extraction_method = event.extraction_method
            session.commit()

    def update_review_status(
        self, event_id: str, review_status: str, *, title: Optional[str] = None, description: Optional[str] = None,
    ) -> Optional[TimelineEvent]:
        with self._session_factory() as session:
            row = session.execute(
                select(TimelineEventRow).where(TimelineEventRow.external_event_id == event_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            row.review_status = review_status
            if title is not None:
                row.title = title
            if description is not None:
                row.description = description
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: TimelineEventRow) -> TimelineEvent:
        return TimelineEvent(
            event_id=row.external_event_id,
            patient_id=row.patient.external_patient_id,
            event_type=row.event_type,
            title=row.title,
            description=row.description,
            observed_date=row.observed_date,
            source_call_id=row.call.external_call_id,
            source_turn_start=row.turn_start,
            source_turn_end=row.turn_end,
            quote=row.quote,
            confidence=row.confidence,
            extraction_method=row.extraction_method,
            review_status=row.review_status,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            dedupe_key=row.dedupe_key,
        )


class PostgresPatternRepository(PatternRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_for_patient(self, patient_id: str) -> List[PatientPattern]:
        with self._session_factory() as session:
            rows = session.execute(
                select(PatternRow)
                .join(PatientRow, PatternRow.patient_id == PatientRow.id)
                .where(PatientRow.external_patient_id == patient_id)
                .order_by(PatternRow.first_observed_date)
            ).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get(self, pattern_id: str) -> Optional[PatientPattern]:
        with self._session_factory() as session:
            row = session.execute(
                select(PatternRow).where(PatternRow.external_pattern_id == pattern_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def upsert_many(self, patterns: List[PatientPattern]) -> None:
        with self._session_factory() as session:
            for pattern in patterns:
                patient_row = session.execute(
                    select(PatientRow).where(PatientRow.external_patient_id == pattern.patient_id)
                ).scalar_one_or_none()
                if patient_row is None:
                    continue

                existing = session.execute(
                    select(PatternRow).where(
                        PatternRow.patient_id == patient_row.id,
                        PatternRow.dedupe_key == pattern.dedupe_key,
                    )
                ).scalar_one_or_none()

                if existing is None:
                    session.add(PatternRow(
                        external_pattern_id=pattern.pattern_id,
                        patient_id=patient_row.id,
                        pattern_type=pattern.pattern_type,
                        title=pattern.title,
                        summary=pattern.summary,
                        status=pattern.status,
                        severity=pattern.severity,
                        first_observed_date=pattern.first_observed_date,
                        latest_observed_date=pattern.latest_observed_date,
                        related_timeline_event_ids=list(pattern.related_timeline_event_ids),
                        related_call_ids=list(pattern.related_call_ids),
                        evidence=[
                            {
                                "timeline_event_id": e.timeline_event_id, "call_id": e.call_id,
                                "turn_start": e.turn_start, "turn_end": e.turn_end, "quote": e.quote,
                            }
                            for e in pattern.evidence
                        ],
                        detector_version=pattern.detector_version,
                        reviewed_status=pattern.reviewed_status,
                        dedupe_key=pattern.dedupe_key,
                    ))
                elif existing.reviewed_status == "unreviewed":
                    # A coordinator's prior review decision always wins over a rebuild.
                    existing.pattern_type = pattern.pattern_type
                    existing.title = pattern.title
                    existing.summary = pattern.summary
                    existing.status = pattern.status
                    existing.severity = pattern.severity
                    existing.first_observed_date = pattern.first_observed_date
                    existing.latest_observed_date = pattern.latest_observed_date
                    existing.related_timeline_event_ids = list(pattern.related_timeline_event_ids)
                    existing.related_call_ids = list(pattern.related_call_ids)
                    existing.evidence = [
                        {
                            "timeline_event_id": e.timeline_event_id, "call_id": e.call_id,
                            "turn_start": e.turn_start, "turn_end": e.turn_end, "quote": e.quote,
                        }
                        for e in pattern.evidence
                    ]
                    existing.detector_version = pattern.detector_version
            session.commit()

    def update_reviewed_status(self, pattern_id: str, reviewed_status: str) -> Optional[PatientPattern]:
        with self._session_factory() as session:
            row = session.execute(
                select(PatternRow).where(PatternRow.external_pattern_id == pattern_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            row.reviewed_status = reviewed_status
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: PatternRow) -> PatientPattern:
        return PatientPattern(
            pattern_id=row.external_pattern_id,
            patient_id=row.patient.external_patient_id,
            pattern_type=row.pattern_type,
            title=row.title,
            summary=row.summary,
            status=row.status,
            severity=row.severity,
            first_observed_date=row.first_observed_date,
            latest_observed_date=row.latest_observed_date,
            related_timeline_event_ids=tuple(row.related_timeline_event_ids),
            related_call_ids=tuple(row.related_call_ids),
            evidence=tuple(
                PatternEvidenceRef(
                    timeline_event_id=e["timeline_event_id"], call_id=e["call_id"],
                    turn_start=e["turn_start"], turn_end=e["turn_end"], quote=e["quote"],
                )
                for e in row.evidence
            ),
            detector_version=row.detector_version,
            reviewed_status=row.reviewed_status,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            dedupe_key=row.dedupe_key,
        )


class PostgresCoordinatorTaskRepository(CoordinatorTaskRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_tasks(
        self,
        *,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[CoordinatorTask]:
        with self._session_factory() as session:
            stmt = select(CoordinatorTaskRow).order_by(CoordinatorTaskRow.created_at)
            if patient_id:
                stmt = stmt.join(PatientRow, CoordinatorTaskRow.patient_id == PatientRow.id).where(
                    PatientRow.external_patient_id == patient_id
                )
            if status:
                stmt = stmt.where(CoordinatorTaskRow.status == status)
            if priority:
                stmt = stmt.where(CoordinatorTaskRow.priority == priority)
            if category:
                stmt = stmt.where(CoordinatorTaskRow.category == category)
            if assignee:
                stmt = stmt.where(CoordinatorTaskRow.assignee == assignee)
            rows = session.execute(stmt).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get(self, task_id: str) -> Optional[CoordinatorTask]:
        with self._session_factory() as session:
            row = session.execute(
                select(CoordinatorTaskRow).where(CoordinatorTaskRow.external_task_id == task_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def find_by_dedupe_key(self, patient_id: str, dedupe_key: str) -> Optional[CoordinatorTask]:
        with self._session_factory() as session:
            row = session.execute(
                select(CoordinatorTaskRow)
                .join(PatientRow, CoordinatorTaskRow.patient_id == PatientRow.id)
                .where(PatientRow.external_patient_id == patient_id, CoordinatorTaskRow.dedupe_key == dedupe_key)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def create(self, task: CoordinatorTask) -> CoordinatorTask:
        with self._session_factory() as session:
            patient_row = session.execute(
                select(PatientRow).where(PatientRow.external_patient_id == task.patient_id)
            ).scalar_one_or_none()
            if patient_row is None:
                raise ValueError(f"Unknown patient {task.patient_id}")

            row = CoordinatorTaskRow(
                external_task_id=task.task_id,
                patient_id=patient_row.id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                status=task.status,
                category=task.category,
                is_suggested=task.is_suggested,
                created_by=task.created_by,
                source_event_id=task.source_event_id,
                source_call_id=task.source_call_id,
                source_turn_start=task.source_turn_start,
                source_turn_end=task.source_turn_end,
                assignee=task.assignee,
                due_date=task.due_date,
                dedupe_key=task.dedupe_key,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    def update(self, task: CoordinatorTask) -> CoordinatorTask:
        with self._session_factory() as session:
            row = session.execute(
                select(CoordinatorTaskRow).where(CoordinatorTaskRow.external_task_id == task.task_id)
            ).scalar_one_or_none()
            if row is None:
                raise ValueError(f"Unknown task {task.task_id}")
            row.title = task.title
            row.description = task.description
            row.priority = task.priority
            row.status = task.status
            row.category = task.category
            row.assignee = task.assignee
            row.due_date = task.due_date
            row.completed_at = (
                datetime.fromisoformat(task.completed_at) if task.completed_at else None
            )
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: CoordinatorTaskRow) -> CoordinatorTask:
        return CoordinatorTask(
            task_id=row.external_task_id,
            title=row.title,
            description=row.description,
            patient_id=row.patient.external_patient_id,
            priority=row.priority,
            status=row.status,
            category=row.category,
            is_suggested=row.is_suggested,
            created_by=row.created_by,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            source_event_id=row.source_event_id,
            source_call_id=row.source_call_id,
            source_turn_start=row.source_turn_start,
            source_turn_end=row.source_turn_end,
            assignee=row.assignee,
            due_date=row.due_date,
            completed_at=row.completed_at.isoformat() if row.completed_at else None,
            dedupe_key=row.dedupe_key,
        )


class PostgresTaskActivityRepository(TaskActivityRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_for_task(self, task_id: str) -> List[TaskActivity]:
        with self._session_factory() as session:
            task_row = session.execute(
                select(CoordinatorTaskRow).where(CoordinatorTaskRow.external_task_id == task_id)
            ).scalar_one_or_none()
            if task_row is None:
                return []
            rows = session.execute(
                select(TaskActivityRow)
                .where(TaskActivityRow.task_id == task_row.id)
                .order_by(TaskActivityRow.created_at)
            ).scalars().all()
            return [self._to_domain(row, task_id) for row in rows]

    def add(self, activity: TaskActivity) -> None:
        with self._session_factory() as session:
            task_row = session.execute(
                select(CoordinatorTaskRow).where(CoordinatorTaskRow.external_task_id == activity.task_id)
            ).scalar_one_or_none()
            if task_row is None:
                return
            session.add(TaskActivityRow(
                external_activity_id=activity.activity_id,
                task_id=task_row.id,
                action=activity.action,
                actor=activity.actor,
                from_status=activity.from_status,
                to_status=activity.to_status,
                note=activity.note,
            ))
            session.commit()

    @staticmethod
    def _to_domain(row: TaskActivityRow, task_id: str) -> TaskActivity:
        return TaskActivity(
            activity_id=row.external_activity_id,
            task_id=task_id,
            action=row.action,
            actor=row.actor,
            created_at=row.created_at.isoformat(),
            from_status=row.from_status,
            to_status=row.to_status,
            note=row.note,
        )


def _bullet_to_dict(bullet: BriefBullet) -> dict:
    return {
        "bullet_id": bullet.bullet_id,
        "section": bullet.section,
        "patient_id": bullet.patient_id,
        "patient_name": bullet.patient_name,
        "summary": bullet.summary,
        "related_timeline_event_ids": list(bullet.related_timeline_event_ids),
        "evidence": [
            {
                "timeline_event_id": e.timeline_event_id, "call_id": e.call_id,
                "turn_start": e.turn_start, "turn_end": e.turn_end, "quote": e.quote,
            }
            for e in bullet.evidence
        ],
        "related_pattern_id": bullet.related_pattern_id,
        "related_task_id": bullet.related_task_id,
    }


def _bullet_from_dict(data: dict) -> BriefBullet:
    return BriefBullet(
        bullet_id=data["bullet_id"],
        section=data["section"],
        patient_id=data["patient_id"],
        patient_name=data["patient_name"],
        summary=data["summary"],
        related_timeline_event_ids=tuple(data["related_timeline_event_ids"]),
        evidence=tuple(
            PatternEvidenceRef(
                timeline_event_id=e["timeline_event_id"], call_id=e["call_id"],
                turn_start=e["turn_start"], turn_end=e["turn_end"], quote=e["quote"],
            )
            for e in data["evidence"]
        ),
        related_pattern_id=data.get("related_pattern_id"),
        related_task_id=data.get("related_task_id"),
    )


class PostgresBriefRepository(BriefRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def create(self, brief: Brief) -> Brief:
        with self._session_factory() as session:
            row = BriefRow(
                external_brief_id=brief.brief_id,
                brief_type=brief.brief_type,
                start_date=brief.start_date,
                end_date=brief.end_date,
                patient_id=brief.patient_id,
                include_resolved=brief.include_resolved,
                bullets=[_bullet_to_dict(b) for b in brief.bullets],
                model_version=brief.model_version,
                prompt_version=brief.prompt_version,
                generated_at=datetime.fromisoformat(brief.generated_at),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    def get(self, brief_id: str) -> Optional[Brief]:
        with self._session_factory() as session:
            row = session.execute(
                select(BriefRow).where(BriefRow.external_brief_id == brief_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def list_briefs(
        self, *, brief_type: Optional[str] = None, patient_id: Optional[str] = None,
    ) -> List[Brief]:
        with self._session_factory() as session:
            stmt = select(BriefRow).order_by(BriefRow.created_at.desc())
            if brief_type:
                stmt = stmt.where(BriefRow.brief_type == brief_type)
            if patient_id:
                stmt = stmt.where(BriefRow.patient_id == patient_id)
            rows = session.execute(stmt).scalars().all()
            return [self._to_domain(row) for row in rows]

    def update(self, brief: Brief) -> Brief:
        with self._session_factory() as session:
            row = session.execute(
                select(BriefRow).where(BriefRow.external_brief_id == brief.brief_id)
            ).scalar_one_or_none()
            if row is None:
                raise ValueError(f"Unknown brief {brief.brief_id}")
            row.bullets = [_bullet_to_dict(b) for b in brief.bullets]
            row.model_version = brief.model_version
            row.prompt_version = brief.prompt_version
            row.generated_at = datetime.fromisoformat(brief.generated_at)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: BriefRow) -> Brief:
        return Brief(
            brief_id=row.external_brief_id,
            brief_type=row.brief_type,
            start_date=row.start_date,
            end_date=row.end_date,
            patient_id=row.patient_id,
            include_resolved=row.include_resolved,
            bullets=tuple(_bullet_from_dict(b) for b in row.bullets),
            model_version=row.model_version,
            prompt_version=row.prompt_version,
            generated_at=row.generated_at.isoformat(),
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )


class PostgresQuestionAuditRepository(QuestionAuditRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def create(self, record: QuestionAudit) -> QuestionAudit:
        with self._session_factory() as session:
            row = QuestionAuditRow(
                external_request_id=record.request_id,
                question_hash=record.question_hash,
                question_preview=record.question_preview,
                filters=record.filters,
                storage_mode=record.storage_mode,
                retrieval_mode=record.retrieval_mode,
                lexical_weight=record.lexical_weight,
                semantic_weight=record.semantic_weight,
                top_k=record.top_k,
                relevance_threshold=record.relevance_threshold,
                candidate_chunk_ids=list(record.candidate_chunk_ids),
                selected_evidence_ids=list(record.selected_evidence_ids),
                answer_mode=record.answer_mode,
                provider=record.provider,
                model_name=record.model_name,
                prompt_version=record.prompt_version,
                token_usage=record.token_usage,
                latency_ms=record.latency_ms,
                answerable=record.answerable,
                confidence=record.confidence,
                final_citation_call_ids=list(record.final_citation_call_ids),
                grounding_checks=record.grounding_checks,
                fallback_used=record.fallback_used,
                error_category=record.error_category,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    def get(self, request_id: str) -> Optional[QuestionAudit]:
        with self._session_factory() as session:
            row = session.execute(
                select(QuestionAuditRow).where(QuestionAuditRow.external_request_id == request_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def list_records(self, *, answerable: Optional[bool] = None, limit: int = 50) -> List[QuestionAudit]:
        with self._session_factory() as session:
            stmt = select(QuestionAuditRow).order_by(QuestionAuditRow.created_at.desc()).limit(limit)
            if answerable is not None:
                stmt = stmt.where(QuestionAuditRow.answerable == answerable)
            rows = session.execute(stmt).scalars().all()
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: QuestionAuditRow) -> QuestionAudit:
        return QuestionAudit(
            request_id=row.external_request_id,
            created_at=row.created_at.isoformat(),
            question_hash=row.question_hash,
            question_preview=row.question_preview,
            filters=row.filters,
            storage_mode=row.storage_mode,
            retrieval_mode=row.retrieval_mode,
            lexical_weight=row.lexical_weight,
            semantic_weight=row.semantic_weight,
            top_k=row.top_k,
            relevance_threshold=row.relevance_threshold,
            candidate_chunk_ids=tuple(row.candidate_chunk_ids),
            selected_evidence_ids=tuple(row.selected_evidence_ids),
            answer_mode=row.answer_mode,
            provider=row.provider,
            model_name=row.model_name,
            prompt_version=row.prompt_version,
            token_usage=row.token_usage,
            latency_ms=row.latency_ms,
            answerable=row.answerable,
            confidence=row.confidence,
            final_citation_call_ids=tuple(row.final_citation_call_ids),
            grounding_checks=row.grounding_checks,
            fallback_used=row.fallback_used,
            error_category=row.error_category,
        )


class PostgresFeedbackRepository(FeedbackRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def create(self, feedback: Feedback) -> Feedback:
        with self._session_factory() as session:
            row = FeedbackRow(
                external_feedback_id=feedback.feedback_id,
                target_type=feedback.target_type,
                target_id=feedback.target_id,
                category=feedback.category,
                actor=feedback.actor,
                comment=feedback.comment,
                corrected_value=feedback.corrected_value,
                prompt_version=feedback.prompt_version,
                retrieval_version=feedback.retrieval_version,
                model_version=feedback.model_version,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    def get(self, feedback_id: str) -> Optional[Feedback]:
        with self._session_factory() as session:
            row = session.execute(
                select(FeedbackRow).where(FeedbackRow.external_feedback_id == feedback_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def list_feedback(
        self,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Feedback]:
        with self._session_factory() as session:
            stmt = select(FeedbackRow).order_by(FeedbackRow.created_at.desc()).limit(limit)
            if target_type:
                stmt = stmt.where(FeedbackRow.target_type == target_type)
            if target_id:
                stmt = stmt.where(FeedbackRow.target_id == target_id)
            if category:
                stmt = stmt.where(FeedbackRow.category == category)
            rows = session.execute(stmt).scalars().all()
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: FeedbackRow) -> Feedback:
        return Feedback(
            feedback_id=row.external_feedback_id,
            target_type=row.target_type,
            target_id=row.target_id,
            category=row.category,
            actor=row.actor,
            created_at=row.created_at.isoformat(),
            comment=row.comment,
            corrected_value=row.corrected_value,
            prompt_version=row.prompt_version,
            retrieval_version=row.retrieval_version,
            model_version=row.model_version,
        )


class PostgresPersonMentionRepository(PersonMentionRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_for_patient(self, patient_id: str) -> List[PersonMention]:
        with self._session_factory() as session:
            rows = session.execute(
                select(PersonMentionRow)
                .join(PatientRow, PersonMentionRow.patient_id == PatientRow.id)
                .where(PatientRow.external_patient_id == patient_id)
                .order_by(PersonMentionRow.turn_number)
            ).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get(self, mention_id: str) -> Optional[PersonMention]:
        with self._session_factory() as session:
            row = session.execute(
                select(PersonMentionRow).where(PersonMentionRow.external_mention_id == mention_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def upsert_many(self, mentions: List[PersonMention]) -> None:
        with self._session_factory() as session:
            for mention in mentions:
                patient_row = session.execute(
                    select(PatientRow).where(PatientRow.external_patient_id == mention.patient_id)
                ).scalar_one_or_none()
                call_row = session.execute(
                    select(CallRow).where(CallRow.external_call_id == mention.source_call_id)
                ).scalar_one_or_none()
                if patient_row is None or call_row is None:
                    continue

                existing = None
                if mention.dedupe_key is not None:
                    existing = session.execute(
                        select(PersonMentionRow).where(
                            PersonMentionRow.call_id == call_row.id,
                            PersonMentionRow.dedupe_key == mention.dedupe_key,
                        )
                    ).scalar_one_or_none()

                if existing is None:
                    session.add(PersonMentionRow(
                        external_mention_id=mention.mention_id,
                        patient_id=patient_row.id,
                        call_id=call_row.id,
                        turn_number=mention.source_turn,
                        quote=mention.quote,
                        role_label=mention.role_label,
                        relationship_type=mention.relationship_type,
                        mentioned_name=mention.mentioned_name,
                        confidence=mention.confidence,
                        extraction_method=mention.extraction_method,
                        review_status=mention.review_status,
                        dedupe_key=mention.dedupe_key,
                    ))
                elif existing.review_status == "unreviewed":
                    # A coordinator's prior review decision always wins over a rebuild.
                    existing.turn_number = mention.source_turn
                    existing.quote = mention.quote
                    existing.role_label = mention.role_label
                    existing.relationship_type = mention.relationship_type
                    existing.mentioned_name = mention.mentioned_name
                    existing.confidence = mention.confidence
                    existing.extraction_method = mention.extraction_method
            session.commit()

    def update_review_status(
        self,
        mention_id: str,
        review_status: str,
        *,
        corrected_relationship_type: Optional[str] = None,
        corrected_name: Optional[str] = None,
    ) -> Optional[PersonMention]:
        with self._session_factory() as session:
            row = session.execute(
                select(PersonMentionRow).where(PersonMentionRow.external_mention_id == mention_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            row.review_status = review_status
            if corrected_relationship_type is not None:
                row.relationship_type = corrected_relationship_type
            if corrected_name is not None:
                row.mentioned_name = corrected_name
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: PersonMentionRow) -> PersonMention:
        return PersonMention(
            mention_id=row.external_mention_id,
            patient_id=row.patient.external_patient_id,
            source_call_id=row.call.external_call_id,
            source_turn=row.turn_number,
            quote=row.quote,
            role_label=row.role_label,
            relationship_type=row.relationship_type,
            confidence=row.confidence,
            extraction_method=row.extraction_method,
            review_status=row.review_status,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            mentioned_name=row.mentioned_name,
            dedupe_key=row.dedupe_key,
        )
