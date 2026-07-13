Report: CareCall Insight

What was built

An internal QA tool for care coordinators: paste a natural-language question about the care-call transcript corpus, get back a grounded answer with citations (patient, call ID, date, exact turn range, quote), and a UI to open the full source transcript.

- Backend (backend/app/): FastAPI service with a hybrid TF-IDF + semantic retriever (retrieval.py) over overlapping 2–4 turn dialogue windows, an answer service that only returns citations backed by trusted transcript metadata (never LLM-generated), and a mock-mode extractive answerer that works with no OpenAI key (real OpenAI calls supported if OPENAI_API_KEY is set).
- Frontend (frontend/src/): React + TypeScript + Vite single-page app — question box, answer panel, citation list, transcript viewer.
- Eval script (scripts/evaluate.py): checks retrieval grounding accuracy against data/carecall_questions.json.

Exact commands to run it

cp .env.example .env
make setup
make backend     # terminal 1 — FastAPI on :8000
make frontend    # terminal 2 — Vite dev server

API root is prefixed /api (e.g. /api/health, /api/ask, /api/calls/{id}).

Test and evaluation results (verified live this session, not just re-described)

- Backend unit tests: python -m pytest backend/tests -v → 8/8 passed.
- Retrieval evaluation: python scripts/evaluate.py → 8/8 questions correctly grounded (including both "no evidence" cases).
- Frontend build: npm run build in frontend/ → succeeds, tsc -b && vite build clean, bundle output in frontend/dist/.
- Live API smoke test: started uvicorn on port 8010, hit /api/health (21 calls loaded, hybrid mode), then /api/ask:
  - "Did the patient report dizziness in June?" → correctly answered with 3 grounded citations (Walter Simmons, Margaret Chen, Samuel Rivera).
  - "Did the patient fall recently?" → correctly refused: answerable: false, empty citations, "not enough evidence" message — confirms the unanswerable-question guardrail works over real HTTP, not just in unit tests.

No fixes were needed this round — the existing commit was already in working order end-to-end.

Commit

fa6f59e Add CareCall Insight: FastAPI retrieval backend, React QA frontend

(Only commit on main; working tree is clean, nothing new to commit this session since verification required no code changes.)

Unfinished / intentionally cut (per README §6–8)

Deliberately out of scope: auth, deployment, durable storage, production vector infra, background ingestion, advanced observability. Noted as future work: stronger evaluation, date/patient filters, better ranking, an ingestion endpoint, safety-highlighting, better observability. Evaluation set is small (8 questions) and the corpus is in-memory only — fine for a demo, not production.

Five files to understand before the debrief

1. backend/app/retrieval.py — hybrid TF-IDF/semantic ranking and chunking logic (the core retrieval design).
2. backend/app/answer_service.py — grounding logic, mock-vs-OpenAI answer generation, unanswerable-question handling.
3. backend/app/main.py — API surface (/api/health, /api/calls, /api/ask) and how citations get attached.
4. scripts/evaluate.py + data/carecall_questions.json — what "correct" means here and how it is measured.
5. README.md — has the demo script, architecture rationale, and the anticipated hands-on Q&A already written out.

Anything requiring your manual action

- .env is present but empty (0 bytes) — ANSWER_MODE defaults to mock so the app runs fine, but if you want real OpenAI-backed answers for the debrief, you need to cp .env.example .env and fill in OPENAI_API_KEY yourself before demoing.
- No secrets are committed; .env is empty and gitignored, so nothing to rotate.