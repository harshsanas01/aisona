import re
from typing import List

from carecall_application.dto.answer import GroundedAnswer
from carecall_application.ports.answer_generator import AnswerGenerator
from carecall_domain import Chunk

UNANSWERABLE_MESSAGE = "I do not have enough evidence in the transcript corpus to answer that confidently."

# Same proper-noun heuristic used by retrieval's named-entity boost and the
# support validator - kept in sync deliberately, see hybrid.py.
_PROPER_NOUN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_QUESTION_STARTER_WORDS = frozenset({
    "Did", "Has", "Have", "Had", "Was", "Were", "Is", "Are", "Should",
    "Would", "Could", "What", "Who", "When", "Where", "Why", "How",
    "Which", "Does", "Do", "Tell", "Can", "Will", "The", "Any",
    # Calendar words are capitalized but are not names - without this a
    # question like "reported feeling dizzy in June?" would treat "June"
    # as a person to match against chunk text, ignoring genuinely dizzy
    # evidence in favor of any unrelated chunk that happens to also
    # mention the word "June".
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Today", "Tomorrow", "Yesterday",
})


class MockAnswerGenerator(AnswerGenerator):
    """Deterministic, offline answer generator. No network calls, no API
    key required - this is what keeps the demo mode fully self-contained."""

    def generate(self, question: str, evidence: List[Chunk], filters: dict) -> GroundedAnswer:
        if not evidence:
            return GroundedAnswer(answerable=False, answer=UNANSWERABLE_MESSAGE, used_evidence_ids=[], confidence="low")

        best = self._select_best_chunk(question, evidence)
        text = self._mock_answer(best)
        used_ids = [best.chunk_id] + [c.chunk_id for c in evidence[:3] if c.chunk_id != best.chunk_id]
        return GroundedAnswer(
            answerable=True, answer=text, used_evidence_ids=used_ids[:3], confidence="high", model_name="mock",
        )

    @staticmethod
    def _select_best_chunk(question: str, chunks: List[Chunk]) -> Chunk:
        # If the question names someone specific, prefer whichever already-
        # relevant chunk actually mentions that name over the top-ranked
        # chunk by fused score alone - retrieval's fused score can still be
        # dominated by generic conversational overlap (greetings, filler
        # verbs) even after boosting, and blindly trusting chunks[0] here is
        # exactly how a question about one person gets answered from
        # another person's unrelated evidence.
        proper_nouns = [
            name for name in _PROPER_NOUN_PATTERN.findall(question)
            if name not in _QUESTION_STARTER_WORDS
        ]
        if proper_nouns:
            for chunk in chunks:
                if any(name in chunk.text for name in proper_nouns):
                    return chunk
        return chunks[0]

    @staticmethod
    def _mock_answer(best: Chunk) -> str:
        # Deliberately extractive rather than templated per keyword bucket:
        # a canned string keyed off e.g. "fall" in the question would give
        # the identical answer for "Did Gus fall?" and "Did Samuel fall?"
        # regardless of which call was actually retrieved - exactly the bug
        # class this system must not have. Quoting the real top-ranked
        # participant turn means the answer always varies with the actual
        # evidence, and a support-validation pass downstream still checks
        # this quote is topically related to the question before it is
        # allowed to reach the caller.
        participant_turns = [t for t in best.turns if t.speaker == "participant"]
        quote = participant_turns[-1].text if participant_turns else best.turns[-1].text
        return f"Based on {best.patient_name}'s call on {best.date}: \"{quote}\""
