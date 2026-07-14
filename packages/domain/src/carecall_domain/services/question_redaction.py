import hashlib


# Normalizes whitespace/case before hashing so trivially-different phrasings
# of the same question ("What meds?" vs "what meds? ") don't produce
# different hashes - the hash is meant to let two audit records be compared
# as "the same question", not to preserve exact text.
def hash_question(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def redact_question_preview(question: str, max_length: int = 60) -> str:
    """A short, truncated preview - never the full question, even when
    retention is explicitly enabled. Callers must still gate calling this
    at all behind an explicit opt-in config flag; this function only
    bounds how much text a preview can ever contain."""
    normalized = " ".join(question.strip().split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length].rstrip() + "…"
