# Bump this whenever TIMELINE_EXTRACTION_PROMPT changes in a way that could
# affect which events are extracted - recorded on every LLM-extracted
# TimelineEvent (extraction_method="llm") for later regression comparison.
TIMELINE_EXTRACTION_PROMPT_VERSION = "v1"

TIMELINE_EXTRACTION_PROMPT = (
    "You identify candidate patient-timeline events in a single care-call transcript. "
    "You are NOT making a medical diagnosis - you are flagging operationally relevant "
    "moments for a human care coordinator to review. "
    "Each transcript turn is numbered. Respond with a JSON object: "
    '{"events": [{"turn_number": int, "event_type": str, "confidence": "high"|"medium"|"low"}, ...]}. '
    "event_type must be one of: medication_started, medication_adherence_concern, symptom_reported, "
    "symptom_recurrence, sleep_issue, meal_concern, transportation_issue, appointment_request, "
    "home_safety_concern, assistive_device_update, issue_resolved, follow_up_promised, other_safety_event. "
    "Only reference turn_number values that actually appear in the transcript you were given. "
    "Do not include a quote, date, or call id in your response - the caller reconstructs those "
    "directly from the transcript, not from your output. "
    "If nothing in the transcript matches any category, return {\"events\": []}."
)
