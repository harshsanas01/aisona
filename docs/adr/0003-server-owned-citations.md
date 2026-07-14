# ADR 0003: Citations are server-owned, never generator-supplied

## Status
Accepted

## Context
An answer generator (mock or LLM) is the least trustworthy component in this system for factual claims about *which call, which turn, which date* something was said - an LLM in particular can hallucinate a plausible-looking call ID or misquote a turn. If citations came directly from generator output, a confident-sounding fabrication would be indistinguishable from a real one to the coordinator reading it.

## Decision
`AnswerGenerator.generate()` may only return `used_evidence_ids` (references to `Chunk.chunk_id` values it was actually given as evidence) alongside free-text `answer`, `confidence`, and provider metadata. It is architecturally incapable of returning a call id, patient id, turn number, quote, or date directly (`GroundedAnswer` has no such fields). `AskQuestionUseCase` reconstructs citations exclusively from the trusted `Chunk` objects retrieval already produced, filtering `used_evidence_ids` down to ones that were actually present in that request's retrieved evidence (a hallucinated id is silently dropped, falling back to the top retrieved chunks rather than emitting a citation-less answer). `StructuralCitationValidator` then does a final sanity check before the response is returned.

## Consequences
- A generator cannot inject a fake citation even if it tries to - the type system and the use case's reconstruction logic don't give it the surface area to do so.
- This applies identically in streaming mode: citations are only ever emitted in the `citations` SSE event, built the same way, after generation has completed and been validated - never streamed speculatively from the model.
- Cost: citation quotes are always built from the same fixed-format turn concatenation (`"speaker: text"` joined by `" | "`, truncated to 220 chars) rather than whatever excerpt the generator might have preferred to highlight - a minor UX trade-off for a correctness guarantee.
