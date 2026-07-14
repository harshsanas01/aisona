import re
from typing import List

from carecall_application.ports.support_validator import SupportValidator
from carecall_domain import Chunk

# Same proper-noun heuristic used by HybridRetriever's named-entity boost:
# a capitalized word in the question is usually a name, but several are only
# capitalized because they start the sentence.
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


class DeterministicSupportValidator(SupportValidator):
    """If the question names someone specific (e.g. "Did Gus fall?"), the
    evidence actually selected for the answer must mention that name
    somewhere - otherwise generation has drifted onto an unrelated call
    (the exact "tomato quote" failure mode: a question about one person
    confidently answered using evidence about someone else entirely).

    Questions with no named entity (most of the corpus's actual usage
    pattern - "Who has been having trouble sleeping?") have nothing to
    check here and pass through.
    """

    def is_supported(self, question: str, evidence_chunks: List[Chunk]) -> bool:
        proper_nouns = [
            name for name in _PROPER_NOUN_PATTERN.findall(question)
            if name not in _QUESTION_STARTER_WORDS
        ]
        if not proper_nouns:
            return True
        combined_text = " ".join(chunk.text for chunk in evidence_chunks)
        return any(name in combined_text for name in proper_nouns)
