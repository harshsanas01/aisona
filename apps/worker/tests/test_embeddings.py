from carecall_worker.embeddings import EMBEDDING_DIM, compute_mock_embedding


def test_embedding_has_expected_dimension():
    vector = compute_mock_embedding("hello world")
    assert len(vector) == EMBEDDING_DIM


def test_embedding_is_deterministic():
    assert compute_mock_embedding("same text") == compute_mock_embedding("same text")


def test_different_text_gives_different_embedding():
    assert compute_mock_embedding("text a") != compute_mock_embedding("text b")


def test_embedding_values_are_bounded():
    vector = compute_mock_embedding("bounds check")
    assert all(-1.0 <= v <= 1.0 for v in vector)
