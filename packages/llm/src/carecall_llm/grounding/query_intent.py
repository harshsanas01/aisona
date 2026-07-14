from dataclasses import dataclass

# Topic categories with no relationship to care-call transcripts. These are
# broad categories, not literal copies of the adversarial test questions, so
# they generalize to new phrasings of the same request ("what's the forecast
# for LA" is caught the same way as "what's today's weather in LA").
_OUT_OF_DOMAIN_MARKERS = [
    "weather", "forecast",
    "super bowl", "world series", "championship", "who won the", "score of the game",
    "bitcoin", "cryptocurrency", "crypto", "stock price", "price of",
    "capital of", "president of", "prime minister of",
    "joke", "riddle", "sing a song", "write a poem", "recite a poem",
]

# A question is treated as advice-seeking (out of scope for a QA tool over
# call transcripts) when it combines an advice-seeking phrasing with a
# medical/clinical topic - e.g. "What medication should Margaret take?" or
# "Should Dorothy visit a doctor?". Purely factual questions about what was
# already discussed ("What new medication did Margaret Chen start?") don't
# match, since they lack the advice-seeking marker.
_ADVICE_MARKERS = ["should", "ought to", "is it safe", "is it okay", "recommend"]
_MEDICAL_TOPIC_MARKERS = [
    "medication", "medicine", "pill", "dose", "dosage", "drug",
    "doctor", "physician", "hospital", "treatment", "diagnosis",
]


@dataclass(frozen=True)
class QueryIntent:
    in_domain: bool
    reason: str = ""


class QueryIntentClassifier:
    """Query validation - the first stage of the grounding pipeline, run
    before retrieval. Deterministic and fully offline. Catches two classes
    of question this tool must never confidently answer regardless of what
    happens to be retrievable: general-knowledge/entertainment requests
    unrelated to care-call transcripts, and requests for clinical advice
    (out of scope for a QA tool that only reports what was discussed).
    """

    def classify(self, question: str) -> QueryIntent:
        lowered = question.lower()

        for marker in _OUT_OF_DOMAIN_MARKERS:
            if marker in lowered:
                return QueryIntent(in_domain=False, reason=f"out_of_domain:{marker}")

        if any(marker in lowered for marker in _ADVICE_MARKERS) and \
                any(marker in lowered for marker in _MEDICAL_TOPIC_MARKERS):
            return QueryIntent(in_domain=False, reason="medical_advice_request")

        return QueryIntent(in_domain=True)
