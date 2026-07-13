# CareCall Insight

CareCall Insight is a small internal QA tool for care coordinators. It loads the provided care-call transcripts, retrieves the most relevant dialogue windows, and returns grounded answers with source citations that can be opened as full transcripts.

## 1. What the project does

A care coordinator can type a natural-language question, receive a concise answer grounded in the transcript corpus, inspect the citations used for that answer, and open the complete source transcript directly from the UI.

## 2. How to run

Prerequisites: Python 3.11+, Node.js 18+, and npm.

```bash
cp .env.example .env
make setup
make backend
```

In a second terminal:

```bash
make frontend
```

Add your OpenAI key to .env if you want OpenAI-backed answer generation. Without it, the app runs in mock mode and still provides grounded extractive answers.

## 3. Architecture overview

```text
React UI
  ↓
FastAPI API
  ↓
Hybrid Retriever
  ↓
Grounded Answer Service
  ↓
Validated citations from original transcript metadata
```

## 4. Retrieval and chunking decisions

- The retriever builds overlapping dialogue windows of 2-4 consecutive turns while preserving the original turn numbers and the exact transcript text.
- Each chunk keeps the patient metadata, date, call ID, and speaker-labelled turns so retrieval can use both lexical and contextual signals.
- The backend uses a TF-IDF lexical ranker and a lightweight semantic similarity signal from the same chunk text; the full corpus is never sent directly to the LLM.
- Citation metadata is built server-side from the trusted transcript metadata rather than from LLM-generated text.

## 5. Unanswerable behavior

Questions that are unsupported by the transcript corpus return an explicit "not enough evidence" response with no citations. The implementation avoids treating negations, third-party mentions, hypothetical questions, and explicit denials as evidence for a participant event.

## 6. Trade-offs and deliberate cuts

This implementation prioritizes a complete, trustworthy QA loop over production infrastructure. Deliberately cut items include authentication, deployment, durable storage, production vector infrastructure, background ingestion, and advanced observability.

## 7. Production-scale evolution

At production scale, the in-memory corpus would be replaced with asynchronous ingestion into durable storage and a searchable index such as OpenSearch, Elasticsearch, pgvector, or a managed vector database. Incremental embedding jobs, metadata filtering, access controls, audit logging, and monitoring would be added as the corpus grows beyond the exercise dataset.

## 8. One more day

With one more day, I would add stronger evaluation, date and patient filters, better ranking, an ingestion endpoint, safety-relevant highlighting, and better observability.

## 9. AI-tool disclosure

AI coding tools helped accelerate scaffolding, test generation, and implementation review; I verified and understood all submitted code.

## Debrief Notes

### Demo flow

1. Ask about dizziness in June.
2. Show the answer and the two cited calls.
3. Open one transcript and show the highlighted evidence.
4. Ask about falls.
5. Show that the system refuses to claim a fall without evidence.

### Architecture explanation

- Retrieval happens before generation so the answer is grounded in evidence instead of free-form generation.
- Chunks preserve dialogue context so adjacent turns remain available to the retriever and the UI.
- Citation metadata is server-owned and mapped back to the original transcript turns.
- Mock mode is supported so the app remains usable without an OpenAI key.
- The retriever can be swapped out at production scale without changing the API contract.

### Known limitations

- The corpus is small and in memory.
- Evaluation is limited to the supplied question set.
- API latency and model cost depend on the configured answer mode.
- Ranking thresholds are heuristic rather than tuned on a large production dataset.
- No production privacy controls or durable ingestion pipeline are implemented.

### Likely hands-on questions

- Where is retrieval ranking implemented? In [backend/app/retrieval.py](backend/app/retrieval.py).
- How is an exact citation mapped back to transcript turns? Through the chunk metadata and the turn range stored in the citation objects.
- What happens when OpenAI fails? The app falls back to the mock answer mode.
- How would you ingest a new call? By adding a new JSON record and extending the ingestion pipeline.
- Why not send all transcripts to the LLM? To keep the prompt small, reduce cost, and preserve grounding.
- Why hybrid search instead of only keyword search? Lexical matching is strong for names and symptoms, while semantic similarity helps with paraphrases such as "trouble sleeping".
- How do you prevent a third party mentioned in a call from being treated as a participant? The app only answers from transcript evidence tied to the corpus participants and uses explicit grounding checks for unsupported questions.
