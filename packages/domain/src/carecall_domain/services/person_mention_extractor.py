import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from ..entities.person_mention import PersonMention
from ..entities.transcript import Call

# Every rule below only matches wording actually observed in the transcript
# corpus (see docs/architecture/event-extraction.md's grounding principle).
# "my X" only ever appears in the participant's own words, so family/neighbor
# possessive rules are restricted to participant turns - the assistant has no
# personal relations relevant to the patient. Staff mentions can appear in
# either speaker's turn (the assistant says "I'll flag this for the nurse";
# the participant says "the physical therapist gave it to me").
_FAMILY_ROLE_WORDS = (
    "daughter", "son", "granddaughter", "grandson", "niece", "nephew",
    "wife", "husband", "sister", "brother", "mother", "father", "mom", "dad",
)

# The (?i:...) scoped flag keeps case-insensitivity contained to the "my
# ROLE" cue - it must not leak onto the [A-Z][a-z]+ name capture below,
# which uses capitalization as its proper-noun signal. A plain re.IGNORECASE
# on the whole pattern would make [A-Z] match any letter, capturing common
# lowercase words like "said" or "brought" as if they were names.
_FAMILY_PATTERN = re.compile(
    r"(?i:\bmy (" + "|".join(_FAMILY_ROLE_WORDS) + r")\b)(?:\s+([A-Z][a-z]+))?",
)

_NEIGHBOR_MY_PATTERN = re.compile(r"(?i:\bmy neighbor\b)(?:\s+([A-Z][a-z]+))?")
_NEIGHBOR_NEXT_DOOR_PATTERN = re.compile(r"\b([A-Z][a-z]+) next door\b")

_STAFF_PATTERNS = [
    (re.compile(r"\bDr\.\s+([A-Z][a-z]+)\b"), "doctor"),
    (re.compile(r"\b(?:the )?nurse\b", re.IGNORECASE), "nurse"),
    (re.compile(r"\b(?:the )?physical therapist\b", re.IGNORECASE), "physical therapist"),
    (re.compile(r"\bcase manager\b", re.IGNORECASE), "case manager"),
    (re.compile(r"\bhome health aide\b", re.IGNORECASE), "home health aide"),
    (re.compile(r"\b(?:the )?podiatrist\b|\bfoot doctor\b", re.IGNORECASE), "doctor"),
    (re.compile(r"\bpharmacist\b", re.IGNORECASE), "pharmacist"),
]

# Deliberately conservative: a third party's relative referred to only by
# pronoun ("his son", "her daughter") cannot be safely attributed to the
# current patient - the son/daughter/etc. named here may belong to someone
# else entirely mentioned earlier in the same turn (e.g. a neighbor). See
# PersonMention's docstring and the Gus/Samuel extraction test.
_AMBIGUOUS_RELATIVE_PATTERN = re.compile(
    r"\b(?:his|her|their) (" + "|".join(_FAMILY_ROLE_WORDS) + r")\b",
    re.IGNORECASE,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersonMentionExtractor(ABC):
    """Turns a single call's transcript into candidate person mentions -
    people other than the patient who are relevant to their care network.
    Deterministic rules are the required, always-available implementation;
    an LLM-backed extractor may implement this same interface, but its
    output must still have every citation field (call_id, turn, quote)
    reconstructed by server code from the real transcript, never trusted
    verbatim from the model - the same server-owned citation reconstruction
    principle as TimelineExtractor (see ADR 0003)."""

    @abstractmethod
    def extract(self, call: Call) -> List[PersonMention]: ...


def build_person_mention(
    call: Call,
    turn_number: int,
    role_label: str,
    relationship_type: str,
    quote: str,
    *,
    mentioned_name: Optional[str] = None,
    confidence: str = "medium",
    extraction_method: str = "deterministic",
) -> PersonMention:
    now = _utcnow_iso()
    role_slug = re.sub(r"[^a-z0-9]+", "_", role_label.lower()).strip("_")
    dedupe_key = f"{relationship_type}:{role_slug}:{mentioned_name or ''}:{turn_number}"
    mention_id = f"pm-{call.call_id}-{turn_number}-{role_slug}"
    return PersonMention(
        mention_id=mention_id,
        patient_id=call.patient.id,
        source_call_id=call.call_id,
        source_turn=turn_number,
        quote=quote,
        role_label=role_label,
        relationship_type=relationship_type,
        confidence=confidence,
        extraction_method=extraction_method,
        review_status="unreviewed",
        created_at=now,
        updated_at=now,
        mentioned_name=mentioned_name,
        dedupe_key=dedupe_key,
    )


class DeterministicPersonMentionExtractor(PersonMentionExtractor):
    """Required, always-available extractor. See module docstring for why
    "my X" possessive rules are restricted to the participant's own turns,
    and why ambiguous third-party pronoun references ("his son") are
    extracted as relationship_type="unknown" rather than guessed."""

    def extract(self, call: Call) -> List[PersonMention]:
        mentions: List[PersonMention] = []
        seen_dedupe_keys = set()

        def _add(turn_number: int, role_label: str, relationship_type: str, quote: str,
                 mentioned_name: Optional[str] = None) -> None:
            mention = build_person_mention(
                call, turn_number, role_label, relationship_type, quote, mentioned_name=mentioned_name,
            )
            if mention.dedupe_key in seen_dedupe_keys:
                return
            seen_dedupe_keys.add(mention.dedupe_key)
            mentions.append(mention)

        for turn_number, turn in enumerate(call.turns, start=1):
            text = turn.text

            if turn.speaker == "participant":
                for match in _FAMILY_PATTERN.finditer(text):
                    role_label, name = match.group(1).lower(), match.group(2)
                    _add(turn_number, role_label, "family", text, mentioned_name=name)

                neighbor_match = _NEIGHBOR_MY_PATTERN.search(text)
                if neighbor_match:
                    _add(turn_number, "neighbor", "neighbor", text, mentioned_name=neighbor_match.group(1))
                for match in _NEIGHBOR_NEXT_DOOR_PATTERN.finditer(text):
                    _add(turn_number, "neighbor", "neighbor", text, mentioned_name=match.group(1))

            for pattern, role_label in _STAFF_PATTERNS:
                staff_match = pattern.search(text)
                if staff_match:
                    name = staff_match.group(1) if staff_match.groups() else None
                    _add(turn_number, role_label, "staff", text, mentioned_name=name)

            for ambiguous_match in _AMBIGUOUS_RELATIVE_PATTERN.finditer(text):
                _add(turn_number, ambiguous_match.group(1).lower(), "unknown", text)

        return mentions
