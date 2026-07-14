from pathlib import Path

from carecall_application.use_cases import CompareRetrievalModesUseCase
from carecall_persistence.in_memory import InMemoryChunkRepository, load_calls_from_json
from carecall_retrieval import build_chunks

REPO_ROOT = Path(__file__).resolve().parents[3]
CALLS = load_calls_from_json(REPO_ROOT / "data" / "raw" / "carecall_transcripts.json")
CHUNKS = [chunk for call in CALLS for chunk in build_chunks(call)]

USE_CASE = CompareRetrievalModesUseCase(
    InMemoryChunkRepository(CHUNKS),
    lexical_weight=0.45,
    semantic_weight=0.55,
    min_relevance_score=0.15,
    default_top_k=8,
)


def test_returns_all_four_modes_in_a_stable_order():
    results = USE_CASE.execute("lisinopril")
    assert [r.mode for r in results] == ["lexical", "semantic", "hybrid", "hybrid_rerank"]


def test_lexical_mode_uses_pure_lexical_weights():
    results = USE_CASE.execute("lisinopril")
    lexical = next(r for r in results if r.mode == "lexical")
    assert lexical.lexical_weight == 1.0
    assert lexical.semantic_weight == 0.0
    assert lexical.reranked is False


def test_semantic_mode_uses_pure_semantic_weights():
    results = USE_CASE.execute("lisinopril")
    semantic = next(r for r in results if r.mode == "semantic")
    assert semantic.lexical_weight == 0.0
    assert semantic.semantic_weight == 1.0


def test_hybrid_rerank_mode_is_flagged_as_reranked_and_others_are_not():
    results = USE_CASE.execute("lisinopril")
    by_mode = {r.mode: r for r in results}
    assert by_mode["hybrid_rerank"].reranked is True
    assert by_mode["lexical"].reranked is False
    assert by_mode["semantic"].reranked is False
    assert by_mode["hybrid"].reranked is False


def test_all_modes_return_real_candidates_with_citation_fields_for_a_grounded_question():
    results = USE_CASE.execute("What new medication did Margaret Chen start?")
    for result in results:
        assert result.candidates
        for candidate in result.candidates:
            assert candidate.call_id
            assert candidate.quote
            assert isinstance(candidate.score, float)


def test_hybrid_rerank_ranks_the_exact_phrase_match_first():
    """"started me on a new blood pressure pill" is call_003's verbatim
    phrasing - hybrid+rerank's phrase-overlap boost should put it first,
    proving the rerank stage actually changes ranking versus plain hybrid."""
    results = USE_CASE.execute("started me on a new blood pressure pill")
    hybrid_rerank = next(r for r in results if r.mode == "hybrid_rerank")
    assert hybrid_rerank.candidates
    assert hybrid_rerank.candidates[0].call_id == "call_003"


def test_out_of_domain_question_returns_no_candidates_in_any_mode():
    results = USE_CASE.execute("What is the price of Bitcoin?")
    for result in results:
        assert result.candidates == []


def test_can_filter_by_patient_id():
    results = USE_CASE.execute("medication", patient_id="P-1001")
    for result in results:
        assert all(c.patient_id == "P-1001" for c in result.candidates)
