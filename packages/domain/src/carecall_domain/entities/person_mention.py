from dataclasses import dataclass
from typing import Optional

PERSON_RELATIONSHIP_TYPES = ("participant", "family", "neighbor", "staff", "unknown")

# "participant" (another CareCall program participant) is never assigned by
# the extractor itself - only a human coordinator can promote a mention to
# it, via PATCH/feedback correction. The extractor cannot safely tell "this
# named person is also enrolled in the program" from transcript text alone.
PERSON_MENTION_REVIEW_STATUSES = ("unreviewed", "confirmed", "corrected", "dismissed")


@dataclass(frozen=True)
class PersonMention:
    """A person other than the patient, referenced somewhere in a call
    transcript - a caregiver, family member, neighbor, or staff contact
    relevant to the patient's care network. Like TimelineEvent, this is an
    "observed transcript mention", not a verified relationship record: every
    field needed to trace it back to the exact transcript moment
    (source_call_id, source_turn, quote) is always present.

    relationship_type is deliberately conservative: when the transcript's
    wording does not unambiguously establish whose relation is being
    described (e.g. "his son" said about a third party, not "my son"),
    extraction assigns "unknown" rather than guessing - this is what keeps a
    neighbor's family member from ever being misattributed as the patient's
    own. A human coordinator resolves "unknown" cases via review_status.

    review_status starts "unreviewed" and is only ever changed by a human
    coordinator (PATCH /api/v1/person-mentions/{mention_id} or an equivalent
    Feedback record) - extraction never marks a mention confirmed/corrected/
    dismissed itself."""

    mention_id: str
    patient_id: str
    source_call_id: str
    source_turn: int
    quote: str
    role_label: str  # e.g. "daughter", "neighbor", "nurse", "son" (free text, human-readable)
    relationship_type: str  # one of PERSON_RELATIONSHIP_TYPES
    confidence: str  # "low" | "medium" | "high"
    extraction_method: str  # "deterministic" | "llm"
    review_status: str  # one of PERSON_MENTION_REVIEW_STATUSES
    created_at: str
    updated_at: str
    mentioned_name: Optional[str] = None
    dedupe_key: Optional[str] = None
