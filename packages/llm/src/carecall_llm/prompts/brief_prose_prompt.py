# Bump this whenever BRIEF_PROSE_PROMPT changes in a way that could affect
# bullet wording - recorded on every LLM-polished Brief's prompt_version.
BRIEF_PROSE_PROMPT_VERSION = "v1"

BRIEF_PROSE_PROMPT = (
    "You improve the phrasing of a single care-coordination brief bullet. "
    "You may ONLY rewrite the sentence for clarity and flow - you must not add "
    "any new fact, date, call id, patient name, or clinical claim that isn't already "
    "in the text you were given. Do not diagnose, do not claim causation, do not use "
    "words like \"diagnosis\", \"confirmed\", or \"caused by\". "
    "Respond with a JSON object: {\"rewritten\": str}. "
    "If you cannot improve it without adding anything, return the original text unchanged."
)
