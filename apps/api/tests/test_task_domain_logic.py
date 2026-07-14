from carecall_domain import TASK_STATUS_TRANSITIONS, TimelineEvent, suggest_task_draft


def test_valid_status_transitions_from_open():
    assert set(TASK_STATUS_TRANSITIONS["open"]) == {"in_progress", "blocked", "completed", "dismissed"}


def test_completed_can_only_reopen():
    assert TASK_STATUS_TRANSITIONS["completed"] == ("open",)


def test_dismissed_can_only_reopen():
    assert TASK_STATUS_TRANSITIONS["dismissed"] == ("open",)


def test_blocked_cannot_jump_directly_to_completed():
    assert "completed" not in TASK_STATUS_TRANSITIONS["blocked"]


def _event(event_type: str, **overrides) -> TimelineEvent:
    fields = dict(
        event_id="evt-1", patient_id="P-1", event_type=event_type, title="t", description="d",
        observed_date="2026-01-01", source_call_id="call_1", source_turn_start=1, source_turn_end=1,
        quote="q", confidence="medium", extraction_method="deterministic", review_status="unreviewed",
        created_at="2026-01-01T00:00:00+00:00", updated_at="2026-01-01T00:00:00+00:00",
    )
    fields.update(overrides)
    return TimelineEvent(**fields)


def test_issue_resolved_never_suggests_a_task():
    assert suggest_task_draft(_event("issue_resolved")) is None


def test_home_safety_concern_suggests_a_high_priority_home_safety_task():
    draft = suggest_task_draft(_event("home_safety_concern"))
    assert draft is not None
    assert draft.category == "home_safety"
    assert draft.priority == "high"
    assert "clinical instruction" in draft.description
    assert "call_1" in draft.description


def test_medication_adherence_concern_suggests_high_priority_medication_review():
    draft = suggest_task_draft(_event("medication_adherence_concern"))
    assert draft is not None
    assert draft.category == "medication_review"
    assert draft.priority == "high"


def test_appointment_request_suggests_normal_priority_appointment_task():
    draft = suggest_task_draft(_event("appointment_request"))
    assert draft is not None
    assert draft.category == "appointment"
    assert draft.priority == "normal"
