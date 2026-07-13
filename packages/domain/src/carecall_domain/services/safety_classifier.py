from abc import ABC, abstractmethod
from typing import List

from ..entities.safety_event import SafetyEvent
from ..entities.transcript import Call

SAFETY_CATEGORIES = (
    "dizziness",
    "fall_or_near_fall",
    "missed_medication",
    "medication_change",
    "sleep_problem",
    "food_or_meal_concern",
    "glucose_concern",
    "respiratory_symptom",
    "transportation_issue",
    "home_safety_concern",
)


class SafetyClassifier(ABC):
    """Flags operationally-relevant turns for care-coordinator triage. This
    is deliberately NOT a medical diagnosis system - severity is a coarse
    triage signal, not a clinical assessment.

    Deterministic rules are the required, always-available implementation
    (must work fully offline). An LLM-backed classifier could implement this
    same interface as an optional, swappable enhancement - see
    docs/architecture/grounding.md for why deterministic rules are required
    to run first regardless of which classifier is configured.
    """

    @abstractmethod
    def classify(self, call: Call) -> List[SafetyEvent]: ...


# Each rule is (category, severity, trigger_phrases, suppress_phrases).
# A turn is flagged for a category if it contains any trigger phrase and
# none of that category's suppress phrases - suppress phrases exist so a
# resolved or explicitly denied mention ("the cough is gone", "no falls")
# isn't flagged as an active concern.
_RULES = [
    ("dizziness", "medium",
     ["dizzy", "dizziness", "lightheaded", "light-headed"],
     ["no dizziness", "not dizzy", "wasn't dizzy", "hasn't felt dizzy"]),

    ("fall_or_near_fall", "high",
     ["i fell", "she fell", "he fell", "fell down", "went down", "tripped", "had a fall"],
     ["didn't fall", "did not fall", "no falls", "hasn't fallen", "has not fallen"]),

    ("fall_or_near_fall", "medium",
     ["nearly lost my balance", "almost fell", "caught myself", "nearly fell",
      "lost my balance but", "grabbed the counter", "grabbed the rail"],
     []),

    ("missed_medication", "medium",
     ["didn't take my", "didn't take any", "missed my dose", "forgot to take",
      "skipped my medication", "didn't take it"],
     []),

    ("medication_change", "low",
     ["started me on a new", "new blood pressure pill", "new medication",
      "new pill", "stopped taking", "changed my dosage", "dosage change"],
     []),

    ("sleep_problem", "low",
     ["trouble sleeping", "can't sleep", "cannot sleep", "waking up around",
      "up before dawn", "hours a night", "nodding off", "trouble falling asleep"],
     []),

    ("food_or_meal_concern", "low",
     ["just have coffee for lunch", "cooking for one", "skipping meals",
      "no appetite", "haven't been eating", "not eating much"],
     []),

    ("glucose_concern", "medium",
     ["sugar's been running high", "blood sugar", "glucose", "sugar was high", "sugar ran high"],
     ["back where they belong", "sugar's back", "one thirties every morning"]),

    ("respiratory_symptom", "low",
     ["dry cough", "a cough", "shortness of breath", "wheezing", "trouble breathing", "chest congestion"],
     ["gone, completely gone", "cough is gone", "cough's gone"]),

    ("transportation_issue", "low",
     ["van was late", "van's late", "van late", "missed the start", "missed my ride", "transportation"],
     ["van's been on time", "van was on time", "on time this week"]),

    ("home_safety_concern", "medium",
     ["slippery", "afraid of slipping", "no railing", "loose rug", "broken step", "smoke detector"],
     ["put in the grab bars", "feel so much safer", "solid as a rock"]),
]


class DeterministicSafetyClassifier(SafetyClassifier):
    def classify(self, call: Call) -> List[SafetyEvent]:
        events: List[SafetyEvent] = []
        for turn_number, turn in enumerate(call.turns, start=1):
            # Only the participant's own words are triage-relevant evidence -
            # the assistant frequently echoes symptom keywords back in a
            # follow-up question ("Any dizziness, swelling, or coughing
            # since...?"), which must never itself count as a report.
            if turn.speaker != "participant":
                continue
            lowered = turn.text.lower()
            for category, severity, triggers, suppressors in _RULES:
                if any(s in lowered for s in suppressors):
                    continue
                matched = next((t for t in triggers if t in lowered), None)
                if matched is None:
                    continue
                events.append(SafetyEvent(
                    category=category,
                    severity=severity,
                    call_id=call.call_id,
                    turn_number=turn_number,
                    matched_text=turn.text,
                    explanation=f"Matched trigger phrase '{matched}' for category '{category}'.",
                    classifier_type="deterministic",
                ))
        return events
