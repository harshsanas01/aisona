from carecall_domain import Chunk, Turn
from carecall_retrieval import IdentityReranker, KeywordOverlapReranker


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        call_id="call_test",
        patient_id="P-TEST",
        patient_name="Test Patient",
        date="2026-01-01",
        turn_start=1,
        turn_end=1,
        turns=[Turn(speaker="participant", text=text)],
        metadata_text="",
        text=text,
    )


def test_identity_reranker_leaves_order_unchanged():
    chunks = [(0.5, _chunk("a", "some text")), (0.9, _chunk("b", "other text"))]
    assert IdentityReranker().rerank("query", chunks) == chunks


def test_exact_phrase_match_is_boosted_above_a_scrambled_word_match():
    """Two chunks share the same three words as the query, but only one
    contains them as the same contiguous phrase - a real reranking signal
    that pure bag-of-words lexical/semantic scoring cannot see."""
    exact_phrase_chunk = _chunk("exact", "She started me on a new blood pressure pill yesterday.")
    scrambled_chunk = _chunk("scrambled", "A new neighbor started asking about my blood pressure pill collection.")

    reranker = KeywordOverlapReranker()
    # Both start with the identical fused score - reranking is the only
    # thing that can separate them.
    scored = [(0.6, scrambled_chunk), (0.6, exact_phrase_chunk)]
    reranked = reranker.rerank("started me on a new blood pressure pill", scored)

    assert reranked[0][1].chunk_id == "exact"


def test_reranker_never_adds_or_removes_candidates():
    chunks = [(0.3, _chunk("a", "one")), (0.7, _chunk("b", "two")), (0.1, _chunk("c", "three"))]
    reranked = KeywordOverlapReranker().rerank("one two three", chunks)
    assert {c.chunk_id for _, c in reranked} == {"a", "b", "c"}
    assert len(reranked) == len(chunks)


def test_reranker_is_a_no_op_when_query_has_no_words():
    chunks = [(0.5, _chunk("a", "text"))]
    assert KeywordOverlapReranker().rerank("???", chunks) == chunks
