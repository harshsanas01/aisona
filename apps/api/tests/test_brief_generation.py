from carecall_domain import CoordinatorTask, DeterministicBriefGenerator, Patient, PatientPattern, TimelineEvent
from carecall_domain.services.brief_generator import PatientBriefInputs

GENERATOR = DeterministicBriefGenerator()
PATIENT = Patient(id="P-1", name="Test Patient", age=80)


def _event(event_type: str, event_id: str = "evt-1", **overrides) -> TimelineEvent:
    fields = dict(
        event_id=event_id, patient_id=PATIENT.id, event_type=event_type, title="t", description=f"Observed: {event_type}",
        observed_date="2026-06-01", source_call_id="call_1", source_turn_start=2, source_turn_end=2,
        quote="a quote", confidence="medium", extraction_method="deterministic", review_status="unreviewed",
        created_at="2026-06-01T00:00:00+00:00", updated_at="2026-06-01T00:00:00+00:00",
    )
    fields.update(overrides)
    return TimelineEvent(**fields)


def _pattern(severity: str, pattern_type: str = "repeated_occurrence", status: str = "active") -> PatientPattern:
    return PatientPattern(
        pattern_id="pat-1", patient_id=PATIENT.id, pattern_type=pattern_type, title="t", summary="pattern summary",
        status=status, severity=severity, first_observed_date="2026-06-01", latest_observed_date="2026-06-05",
        related_timeline_event_ids=("evt-1",), related_call_ids=("call_1",), evidence=(),
        detector_version="v1", reviewed_status="unreviewed",
        created_at="2026-06-01T00:00:00+00:00", updated_at="2026-06-01T00:00:00+00:00",
    )


def _task(status: str, source_event_id=None, completed_at=None) -> CoordinatorTask:
    return CoordinatorTask(
        task_id="task-1", title="Follow up", description="d", patient_id=PATIENT.id, priority="normal",
        status=status, category="general_outreach", is_suggested=False, created_by="coordinator",
        created_at="2026-06-01T00:00:00+00:00", updated_at="2026-06-01T00:00:00+00:00",
        source_event_id=source_event_id, completed_at=completed_at,
    )


def test_high_attention_pattern_produces_a_high_attention_bullet():
    inputs = [PatientBriefInputs(patient=PATIENT, patterns=[_pattern("high_attention")])]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-07",
        patient_id=None, include_resolved=False, inputs=inputs,
    )
    sections = [b.section for b in brief.bullets]
    assert "high_attention" in sections


def test_attention_severity_pattern_appears_only_under_recurring_concerns_not_high_attention():
    inputs = [PatientBriefInputs(patient=PATIENT, patterns=[_pattern("attention", "repeated_missed_medication")])]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-07",
        patient_id=None, include_resolved=False, inputs=inputs,
    )
    sections = [b.section for b in brief.bullets]
    assert sections == ["recurring_concerns"]


def test_medication_started_event_produces_a_bullet_with_evidence():
    inputs = [PatientBriefInputs(patient=PATIENT, events=[_event("medication_started")])]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-01",
        patient_id=None, include_resolved=False, inputs=inputs,
    )
    assert len(brief.bullets) == 1
    bullet = brief.bullets[0]
    assert bullet.section == "new_medication_changes"
    assert bullet.evidence[0].call_id == "call_1"


def test_unresolved_task_produces_follow_up_needed_bullet_linked_to_its_source_event():
    event = _event("home_safety_concern")
    task = _task("open", source_event_id="evt-1")
    inputs = [PatientBriefInputs(patient=PATIENT, events=[event], unresolved_tasks=[task])]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-01",
        patient_id=None, include_resolved=False, inputs=inputs,
    )
    follow_up = [b for b in brief.bullets if b.section == "follow_up_needed"]
    assert len(follow_up) == 1
    assert follow_up[0].related_task_id == "task-1"
    assert follow_up[0].evidence[0].call_id == "call_1"

    # a rollup task_status_summary bullet is also produced
    assert any(b.section == "task_status_summary" for b in brief.bullets)


def test_resolved_items_are_excluded_unless_include_resolved_is_true():
    inputs = [PatientBriefInputs(patient=PATIENT, patterns=[_pattern("informational", status="resolved")])]

    excluded = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-07",
        patient_id=None, include_resolved=False, inputs=inputs,
    )
    assert not any(b.section == "resolved_items" for b in excluded.bullets)

    included = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-07",
        patient_id=None, include_resolved=True, inputs=inputs,
    )
    assert any(b.section == "resolved_items" for b in included.bullets)


def test_dismissed_tasks_never_appear_in_a_brief():
    inputs = [PatientBriefInputs(patient=PATIENT, unresolved_tasks=[], resolved_tasks=[])]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-01",
        patient_id=None, include_resolved=True, inputs=inputs,
    )
    assert brief.bullets == ()


def test_patient_with_no_data_produces_no_bullets():
    inputs = [PatientBriefInputs(patient=PATIENT)]
    brief = GENERATOR.generate(
        brief_type="daily", start_date="2026-06-01", end_date="2026-06-01",
        patient_id=None, include_resolved=True, inputs=inputs,
    )
    assert brief.bullets == ()
