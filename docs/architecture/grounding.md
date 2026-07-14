# Grounding: the 11-step pipeline, and the bug it replaced

## The bug

A manual test asked "What is today's weather in LA?" and the (pre-refactor) system answered confidently, citing an unrelated quote about a coordinator's tomato garden. A second instance, found empirically while building the fix described here: "Tell me a joke." returned `answerable: true` citing three unrelated calls, with the answer text `"Ha! Bye, Amy."` - the last line of whichever call happened to score just above the relevance threshold on the generic word "tell". A third: "Did Gus fall?", "Did Samuel fall?", and "Did Margaret fall?" all returned the *identical* canned string ("The corpus does not establish that a participant recently fell") regardless of which call was actually retrieved - which is simply wrong for Gus, whose fall (call_021, reported by his neighbor Samuel Rivera) the corpus does establish.

None of these were LLM hallucinations - they happened in **mock mode**, with no model involved at all. The root causes were: (1) a purely statistical relevance score that a generic word can nudge over threshold, (2) canned per-keyword-bucket answer templates that can't distinguish between different people or calls, and (3) no independent check, after generation, that the evidence actually relates to the question. Fixing this meant treating "is this question answerable" as a pipeline with multiple independent, composable defenses - not a single smarter retrieval score.

## The pipeline

Implemented across `AskQuestionUseCase.execute()`/`.stream()` (orchestration) and `packages/llm/grounding/` (the pluggable stages):

1. **Filter validation** - `DateRange(start, end)` raises `InvalidDateRangeError` (-> HTTP 422) before anything else runs.
2. **Query validation / scope classification** - `AnswerabilityGate.is_query_out_of_scope()`, implemented by `QueryIntentClassifier`. Rejects out-of-domain topics (weather, sports, crypto, geography trivia, jokes/entertainment) and medical-advice-seeking phrasing ("What medication should X take?", "Should X visit a doctor?") by topic category before a retrieval call is even made.
3. **Metadata filtering** - patient id / date range, applied inside retrieval.
4. **Candidate retrieval** - `HybridRetriever.retrieve()` (see [retrieval.md](retrieval.md)).
5. **Minimum relevance gating** - retrieval drops anything below `CARECALL_MIN_RELEVANCE_SCORE` before returning.
6. **Evidence diversification** - retrieval's `_diversify()` spreads results across calls.
7. **Answerability gate (evidence-level)** - `AnswerabilityGate.is_unanswerable(question, chunks)`: if evidence is empty, or a known no-evidence-in-corpus pattern (chest pain, an explicit fall-negation phrasing) matches, short-circuit to unanswerable **without ever calling the answer generator**.
8. **Answer generation** - `AnswerGenerator.generate()` (mock: genuinely extractive, quoting the real top-matched turn rather than a canned string keyed on a keyword bucket; OpenAI: structured JSON output, validated against a pydantic schema, with retry/backoff and a fallback to mock on any failure).
9. **Evidence ID validation** - only evidence ids the generator claims to have used, that were *actually present* in the retrieved chunks, are kept; if none are valid, the top-3 retrieved chunks are used instead. A generator can never inject an id, call, patient, turn number, quote, or date that wasn't already server-side evidence.
10. **Post-generation support validation** - `SupportValidator.is_supported(question, selected_chunks)`, implemented by `DeterministicSupportValidator`: if the question names someone specific (a capitalized word that isn't a sentence-starter or calendar word), the selected evidence must actually mention that name, or the answer is rejected. This is the check that stops a "Did Samuel fall?" question from ever being answered using unrelated evidence about a different person, even if retrieval's fused score ranked that unrelated chunk first.
11. **Citation reconstruction and structural validation** - citations are built *only* from server-owned chunk metadata (never from generator output), then `CitationValidator.validate()` (implemented by `StructuralCitationValidator`) drops anything with an empty quote or an inconsistent turn range before the response is returned.

If any gate at steps 2, 7, 8, 10, or 11 rejects, the response is exactly:

```json
{"answerable": false, "confidence": "low", "answer": "The care-call transcripts do not contain enough evidence to answer this question.", "citations": []}
```

## Distinguishing what the spec calls out

- **Participants vs. third parties**: the named-entity retrieval boost and the support validator both operate on literal name matches in transcript text, not on "is this person a registered patient" - so a real third-party event (Gus's fall, reported by Samuel) is still answerable, while a *different* patient's own denial ("Solid as a rock... no trips or stumbles") is what actually grounds a "Did Samuel fall?" answer.
- **Falls vs. near-falls**: `DeterministicSafetyClassifier` (used by the safety-highlighting feature, not the QA pipeline) has separate trigger phrase sets for a completed fall ("fell", "tripped") vs. a near-fall ("nearly lost my balance", "caught myself") - see `packages/domain/src/carecall_domain/services/safety_classifier.py`.
- **Symptoms vs. denied symptoms**: safety classification uses suppressor phrases ("gone, completely gone", "no dizziness") to avoid flagging a resolved or explicitly denied symptom as an active concern.
- **Corpus facts vs. outside knowledge**: step 2's out-of-domain classifier plus retrieval's relevance gate together mean an answer can only ever be grounded in retrieved transcript text - there is no path from "the model happens to know the capital of France" to an answer.
- **Informational answers vs. medical advice**: step 2 rejects advice-seeking phrasing combined with a medical topic before generation runs at all, rather than trusting a generator not to overstep.

## Deliberately not the whole story

Every stage above is deterministic and testable offline. `docs/adr/0003-server-owned-citations.md` explains why citations specifically must never come from generator output, and `data/evaluation/adversarial_questions.json` + `scripts/evaluate_grounding.py` are what keep this pipeline honest over time - a regression here should show up as a failing evaluation run, not a manual QA finding.
