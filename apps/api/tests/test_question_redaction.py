from carecall_domain import hash_question, redact_question_preview


def test_hash_is_stable_for_the_same_question():
    assert hash_question("What medication did Margaret start?") == hash_question("What medication did Margaret start?")


def test_hash_normalizes_whitespace_and_case():
    assert hash_question("What medication?") == hash_question("  what   MEDICATION? ")


def test_hash_differs_for_different_questions():
    assert hash_question("What medication?") != hash_question("What symptom?")


def test_hash_never_contains_the_original_text():
    digest = hash_question("Did anyone mention chest pain?")
    assert "chest pain" not in digest
    assert len(digest) == 64


def test_redact_preview_truncates_long_questions():
    long_question = "Has any participant mentioned feeling dizzy or lightheaded after starting a new medication recently?"
    preview = redact_question_preview(long_question, max_length=40)
    assert len(preview) <= 41  # allows for the trailing ellipsis character
    assert preview.endswith("…")


def test_redact_preview_returns_short_questions_unchanged():
    short_question = "What new medication?"
    assert redact_question_preview(short_question, max_length=60) == short_question


def test_redact_preview_normalizes_whitespace():
    assert redact_question_preview("  What   medication?  ") == "What medication?"
