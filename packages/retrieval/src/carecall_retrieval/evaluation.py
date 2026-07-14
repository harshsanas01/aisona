from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class RetrievalQuestionResult:
    question_id: str
    expected: Sequence[str]
    cited: Sequence[str]
    answerable: bool
    recall: float
    precision: float
    reciprocal_rank: float
    hit: bool


def evaluate_retrieval_question(
    question_id: str, expected: Sequence[str], cited: Sequence[str], answerable: bool,
) -> RetrievalQuestionResult:
    """Recall/precision/MRR against an expected_source_calls fixture, plus a
    'hit' flag (every expected call_id is present among cited - the original
    exercise's own scoring definition) and a special case for
    unanswerable-by-design questions (empty expected list)."""
    expected_set = set(expected)
    cited_set = set(cited)

    if not expected_set:
        hit = not cited and not answerable
        score = 1.0 if hit else 0.0
        return RetrievalQuestionResult(question_id, expected, cited, answerable, score, score, score, hit)

    matched = expected_set & cited_set
    recall = len(matched) / len(expected_set)
    precision = len(matched) / len(cited_set) if cited_set else 0.0
    reciprocal_rank = 0.0
    for rank, call_id in enumerate(cited, start=1):
        if call_id in expected_set:
            reciprocal_rank = 1.0 / rank
            break
    hit = expected_set.issubset(cited_set)
    return RetrievalQuestionResult(question_id, expected, cited, answerable, recall, precision, reciprocal_rank, hit)


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    results: List[RetrievalQuestionResult]

    def _mean(self, attr: str) -> float:
        if not self.results:
            return 0.0
        return sum(getattr(r, attr) for r in self.results) / len(self.results)

    @property
    def mean_recall(self) -> float:
        return self._mean("recall")

    @property
    def mean_precision(self) -> float:
        return self._mean("precision")

    @property
    def mean_reciprocal_rank(self) -> float:
        return self._mean("reciprocal_rank")

    @property
    def hit_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.hit) / len(self.results)

    @property
    def unanswerable_accuracy(self) -> float:
        unanswerable_qs = [r for r in self.results if not r.expected]
        if not unanswerable_qs:
            return 1.0
        correct = [r for r in unanswerable_qs if not r.answerable and not r.cited]
        return len(correct) / len(unanswerable_qs)
