from datetime import datetime, timedelta, timezone
from typing import List, Optional

from carecall_domain import BRIEF_TYPES, Brief, BriefGenerator, InvalidBriefRequestError, PatientBriefInputs

from ..ports.brief_prose_generator import BriefProseGenerator
from ..ports.repositories import (
    BriefRepository,
    CoordinatorTaskRepository,
    PatientRepository,
    PatternRepository,
    TimelineEventRepository,
)


def _default_date_range(brief_type: str) -> tuple:
    today = datetime.now(timezone.utc).date()
    if brief_type == "weekly":
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    return today.isoformat(), today.isoformat()


class GenerateBriefUseCase:
    """Builds a brief strictly from already-persisted structured data:
    timeline events, patterns, and tasks - never directly from transcripts.
    See ADR: structured events before LLM summaries."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        timeline_event_repository: TimelineEventRepository,
        pattern_repository: PatternRepository,
        task_repository: CoordinatorTaskRepository,
        brief_repository: BriefRepository,
        generator: BriefGenerator,
    ):
        self.patient_repository = patient_repository
        self.timeline_event_repository = timeline_event_repository
        self.pattern_repository = pattern_repository
        self.task_repository = task_repository
        self.brief_repository = brief_repository
        self.generator = generator

    def execute(
        self,
        *,
        brief_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        patient_id: Optional[str] = None,
        include_resolved: bool = False,
        prose_generator: Optional[BriefProseGenerator] = None,
    ) -> Brief:
        brief = self.build(
            brief_type=brief_type, start_date=start_date, end_date=end_date,
            patient_id=patient_id, include_resolved=include_resolved,
        )
        if prose_generator is not None:
            brief = prose_generator.polish(brief)
        return self.brief_repository.create(brief)

    def build(
        self,
        *,
        brief_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        patient_id: Optional[str] = None,
        include_resolved: bool = False,
    ) -> Brief:
        """Builds a fresh Brief without persisting it - used both by
        execute() and by RegenerateBriefUseCase, which persists the result
        under the *existing* brief_id instead of creating a new row."""
        if brief_type not in BRIEF_TYPES:
            raise InvalidBriefRequestError(f"'{brief_type}' is not a valid brief type; must be one of {BRIEF_TYPES}")

        if start_date is None or end_date is None:
            default_start, default_end = _default_date_range(brief_type)
            start_date = start_date or default_start
            end_date = end_date or default_end
        if start_date > end_date:
            raise InvalidBriefRequestError(f"start_date ({start_date}) must not be after end_date ({end_date})")

        if patient_id is not None:
            patient = self.patient_repository.get_patient(patient_id)
            patients = [patient] if patient is not None else []
        else:
            patients = self.patient_repository.list_patients()

        inputs: List[PatientBriefInputs] = [
            self._inputs_for_patient(p, start_date, end_date, include_resolved) for p in patients
        ]

        return self.generator.generate(
            brief_type=brief_type, start_date=start_date, end_date=end_date,
            patient_id=patient_id, include_resolved=include_resolved, inputs=inputs,
        )

    def _inputs_for_patient(self, patient, start_date: str, end_date: str, include_resolved: bool):
        events = [
            e for e in self.timeline_event_repository.list_for_patient(patient.id)
            if start_date <= e.observed_date <= end_date
        ]
        patterns = [
            p for p in self.pattern_repository.list_for_patient(patient.id)
            if not (p.latest_observed_date < start_date or p.first_observed_date > end_date)
        ]
        all_tasks = self.task_repository.list_tasks(patient_id=patient.id)
        unresolved_tasks = [t for t in all_tasks if t.status in ("open", "in_progress", "blocked")]
        resolved_tasks = []
        if include_resolved:
            resolved_tasks = [
                t for t in all_tasks
                if t.status == "completed" and t.completed_at
                and start_date <= t.completed_at[:10] <= end_date
            ]
        return PatientBriefInputs(
            patient=patient, events=events, patterns=patterns,
            unresolved_tasks=unresolved_tasks, resolved_tasks=resolved_tasks,
        )
