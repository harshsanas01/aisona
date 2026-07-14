import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..entities.brief import Brief, BriefBullet
from ..entities.coordinator_task import CoordinatorTask
from ..entities.patient import Patient
from ..entities.patient_pattern import PatientPattern
from ..entities.pattern_evidence_ref import PatternEvidenceRef
from ..entities.timeline_event import TimelineEvent

BRIEF_GENERATOR_VERSION = "v1"
BRIEF_PROMPT_VERSION = "v1"

_UNRESOLVED_TASK_STATUSES = ("open", "in_progress", "blocked")

# Pattern types already severity="high_attention" would otherwise show
# twice (once under high_attention, once under recurring_concerns) - this
# set is only used to decide whether a *non*-high_attention recurring
# pattern still deserves its own bullet.
_RECURRING_PATTERN_TYPES = {
    "repeated_occurrence",
    "repeated_transportation_issue",
    "repeated_missed_medication",
    "repeated_sleep_issue",
    "repeated_meal_concern",
    "increasing_frequency",
    "recurrence_after_resolution",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PatientBriefInputs:
    """Everything a brief generator needs for one patient, already filtered
    to the requested date range and resolved/unresolved scope by the
    caller (RebuildBriefUseCase) - the generator itself only selects and
    formats, it never reasons about dates or fetches data on its own."""

    patient: Patient
    events: List[TimelineEvent] = field(default_factory=list)
    patterns: List[PatientPattern] = field(default_factory=list)
    unresolved_tasks: List[CoordinatorTask] = field(default_factory=list)
    resolved_tasks: List[CoordinatorTask] = field(default_factory=list)


class BriefGenerator(ABC):
    """Builds a Brief entirely from already-persisted structured data
    (timeline events, patterns, tasks) - never from raw transcripts
    directly. An LLM-backed prose-polishing stage may run afterward (see
    BriefProseGenerator) but never through this interface: this interface's
    job is exclusively deterministic bullet selection."""

    @abstractmethod
    def generate(
        self,
        *,
        brief_type: str,
        start_date: str,
        end_date: str,
        patient_id: Optional[str],
        include_resolved: bool,
        inputs: List[PatientBriefInputs],
    ) -> Brief: ...


class DeterministicBriefGenerator(BriefGenerator):
    def generate(
        self,
        *,
        brief_type: str,
        start_date: str,
        end_date: str,
        patient_id: Optional[str],
        include_resolved: bool,
        inputs: List[PatientBriefInputs],
    ) -> Brief:
        bullets: List[BriefBullet] = []
        for patient_inputs in inputs:
            bullets.extend(self._bullets_for_patient(patient_inputs, include_resolved))

        now = _utcnow_iso()
        return Brief(
            brief_id=f"brief-{uuid.uuid4().hex[:12]}",
            brief_type=brief_type,
            start_date=start_date,
            end_date=end_date,
            patient_id=patient_id,
            include_resolved=include_resolved,
            bullets=tuple(bullets),
            model_version="deterministic",
            prompt_version=BRIEF_PROMPT_VERSION,
            generated_at=now,
            created_at=now,
            updated_at=now,
        )

    def _bullets_for_patient(self, inputs: PatientBriefInputs, include_resolved: bool) -> List[BriefBullet]:
        patient_id, patient_name = inputs.patient.id, inputs.patient.name
        events_by_id: Dict[str, TimelineEvent] = {e.event_id: e for e in inputs.events}
        bullets: List[BriefBullet] = []

        for pattern in inputs.patterns:
            if pattern.severity == "high_attention":
                bullets.append(self._pattern_bullet("high_attention", patient_id, patient_name, pattern))

        for task in inputs.unresolved_tasks:
            bullets.append(self._task_bullet("follow_up_needed", patient_id, patient_name, task, events_by_id))

        for event in inputs.events:
            if event.event_type == "medication_started":
                bullets.append(self._event_bullet("new_medication_changes", patient_id, patient_name, event))

        for pattern in inputs.patterns:
            if pattern.severity != "high_attention" and pattern.pattern_type in _RECURRING_PATTERN_TYPES:
                bullets.append(self._pattern_bullet("recurring_concerns", patient_id, patient_name, pattern))

        for event in inputs.events:
            if event.event_type in ("transportation_issue", "appointment_request"):
                bullets.append(
                    self._event_bullet("transportation_appointment_issues", patient_id, patient_name, event)
                )

        if include_resolved:
            for pattern in inputs.patterns:
                if pattern.status == "resolved":
                    bullets.append(self._pattern_bullet("resolved_items", patient_id, patient_name, pattern))
            for task in inputs.resolved_tasks:
                bullets.append(self._task_bullet("resolved_items", patient_id, patient_name, task, events_by_id))

        if inputs.unresolved_tasks or inputs.resolved_tasks:
            bullets.append(self._task_status_summary_bullet(patient_id, patient_name, inputs))

        return bullets

    @staticmethod
    def _pattern_bullet(section: str, patient_id: str, patient_name: str, pattern: PatientPattern) -> BriefBullet:
        return BriefBullet(
            bullet_id=f"bul-{uuid.uuid4().hex[:10]}",
            section=section,
            patient_id=patient_id,
            patient_name=patient_name,
            summary=pattern.summary,
            related_timeline_event_ids=pattern.related_timeline_event_ids,
            evidence=pattern.evidence,
            related_pattern_id=pattern.pattern_id,
        )

    @staticmethod
    def _event_bullet(section: str, patient_id: str, patient_name: str, event: TimelineEvent) -> BriefBullet:
        ref = PatternEvidenceRef(
            timeline_event_id=event.event_id, call_id=event.source_call_id,
            turn_start=event.source_turn_start, turn_end=event.source_turn_end, quote=event.quote,
        )
        return BriefBullet(
            bullet_id=f"bul-{uuid.uuid4().hex[:10]}",
            section=section,
            patient_id=patient_id,
            patient_name=patient_name,
            summary=event.description,
            related_timeline_event_ids=(event.event_id,),
            evidence=(ref,),
        )

    @staticmethod
    def _task_bullet(
        section: str, patient_id: str, patient_name: str, task: CoordinatorTask,
        events_by_id: Dict[str, TimelineEvent],
    ) -> BriefBullet:
        related_ids: tuple = ()
        evidence: tuple = ()
        source_event = events_by_id.get(task.source_event_id) if task.source_event_id else None
        if source_event is not None:
            related_ids = (source_event.event_id,)
            evidence = (PatternEvidenceRef(
                timeline_event_id=source_event.event_id, call_id=source_event.source_call_id,
                turn_start=source_event.source_turn_start, turn_end=source_event.source_turn_end,
                quote=source_event.quote,
            ),)
        elif task.source_call_id:
            evidence = (PatternEvidenceRef(
                timeline_event_id="", call_id=task.source_call_id,
                turn_start=task.source_turn_start or 0, turn_end=task.source_turn_end or 0, quote="",
            ),)
        return BriefBullet(
            bullet_id=f"bul-{uuid.uuid4().hex[:10]}",
            section=section,
            patient_id=patient_id,
            patient_name=patient_name,
            summary=f"{task.title} ({task.status.replace('_', ' ')}, {task.priority} priority).",
            related_timeline_event_ids=related_ids,
            evidence=evidence,
            related_task_id=task.task_id,
        )

    @staticmethod
    def _task_status_summary_bullet(patient_id: str, patient_name: str, inputs: PatientBriefInputs) -> BriefBullet:
        counts: Dict[str, int] = {}
        for task in [*inputs.unresolved_tasks, *inputs.resolved_tasks]:
            counts[task.status] = counts.get(task.status, 0) + 1
        summary_parts = ", ".join(f"{count} {status.replace('_', ' ')}" for status, count in sorted(counts.items()))
        return BriefBullet(
            bullet_id=f"bul-{uuid.uuid4().hex[:10]}",
            section="task_status_summary",
            patient_id=patient_id,
            patient_name=patient_name,
            summary=f"Task status: {summary_parts}.",
            related_timeline_event_ids=(),
            evidence=(),
        )
