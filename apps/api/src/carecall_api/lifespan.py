from contextlib import asynccontextmanager
from dataclasses import dataclass

from carecall_application.ports.repositories import CallRepository, ChunkRepository, PatientRepository
from carecall_application.use_cases import (
    AskQuestionUseCase,
    GetCallUseCase,
    IngestCallUseCase,
    ListCallsUseCase,
    ListPatientsUseCase,
    ListSafetyEventsUseCase,
)
from carecall_domain import DeterministicSafetyClassifier
from carecall_llm.grounding import (
    DeterministicSupportValidator,
    HeuristicAnswerabilityGate,
    StructuralCitationValidator,
)
from carecall_llm.providers import MockAnswerGenerator, OpenAIAnswerGenerator
from carecall_persistence.in_memory import (
    InMemoryCallRepository,
    InMemoryChunkRepository,
    InMemoryPatientRepository,
    load_calls_from_json,
)
from carecall_retrieval import HybridRetriever, build_chunks
from fastapi import FastAPI

from . import config


@dataclass
class Container:
    call_repository: CallRepository
    patient_repository: PatientRepository
    chunk_repository: ChunkRepository
    ask_question: AskQuestionUseCase
    list_calls: ListCallsUseCase
    get_call: GetCallUseCase
    ingest_call: IngestCallUseCase
    list_patients: ListPatientsUseCase
    list_safety_events: ListSafetyEventsUseCase


def build_container() -> Container:
    """Wires concrete implementations into the application layer's ports.
    This is the one place that knows about storage mode / answer mode /
    retrieval tuning - swapping demo mode for production-like mode (or mock
    for OpenAI) only ever touches this function."""
    if config.STORAGE_MODE == "postgres":
        call_repository, patient_repository, chunk_repository = _build_postgres_repositories()
    else:
        call_repository, patient_repository, chunk_repository = _build_memory_repositories()

    retrieval_service = HybridRetriever(
        chunk_repository.all_chunks(),
        lexical_weight=config.LEXICAL_WEIGHT,
        semantic_weight=config.SEMANTIC_WEIGHT,
        min_relevance_score=config.MIN_RELEVANCE_SCORE,
        default_top_k=config.TOP_K,
    )

    if config.ANSWER_MODE == "openai" and config.OPENAI_API_KEY:
        answer_generator = OpenAIAnswerGenerator(api_key=config.OPENAI_API_KEY, model=config.OPENAI_CHAT_MODEL)
    else:
        answer_generator = MockAnswerGenerator()

    answerability_gate = HeuristicAnswerabilityGate()
    support_validator = DeterministicSupportValidator()
    citation_validator = StructuralCitationValidator()

    ask_question = AskQuestionUseCase(
        retrieval_service,
        answer_generator,
        answerability_gate,
        support_validator,
        citation_validator,
        default_limit=config.TOP_K,
    )

    def _refresh_retrieval_index() -> None:
        retrieval_service.refresh(chunk_repository.all_chunks())

    ingest_call = IngestCallUseCase(
        call_repository, chunk_repository, build_chunks, on_ingested=_refresh_retrieval_index,
    )

    return Container(
        call_repository=call_repository,
        patient_repository=patient_repository,
        chunk_repository=chunk_repository,
        ask_question=ask_question,
        list_calls=ListCallsUseCase(call_repository),
        get_call=GetCallUseCase(call_repository),
        ingest_call=ingest_call,
        list_patients=ListPatientsUseCase(patient_repository),
        list_safety_events=ListSafetyEventsUseCase(call_repository, DeterministicSafetyClassifier()),
    )


def _build_memory_repositories():
    calls = load_calls_from_json(config.TRANSCRIPTS_PATH)
    call_repository = InMemoryCallRepository(calls)
    patient_repository = InMemoryPatientRepository(call_repository)
    chunks = [chunk for call in calls for chunk in build_chunks(call)]
    chunk_repository = InMemoryChunkRepository(chunks)
    return call_repository, patient_repository, chunk_repository


def _build_postgres_repositories():
    # Imported lazily so sqlalchemy/psycopg/pgvector are only required when
    # CARECALL_STORAGE_MODE=postgres is actually selected - demo mode and
    # unit tests never need them installed.
    from carecall_persistence.postgres import (
        PostgresCallRepository,
        PostgresChunkRepository,
        PostgresPatientRepository,
        create_session_factory,
    )

    session_factory = create_session_factory(config.DATABASE_URL)
    call_repository = PostgresCallRepository(session_factory)
    patient_repository = PostgresPatientRepository(session_factory)
    chunk_repository = PostgresChunkRepository(session_factory)

    # First boot against an empty database: bootstrap from the demo fixture
    # so production-like mode has the same starting corpus as memory mode.
    # Later ingestion (POST /api/calls) adds calls incrementally from here.
    if not call_repository.list_calls():
        for call in load_calls_from_json(config.TRANSCRIPTS_PATH):
            call_repository.add_call(call)
            chunk_repository.add_chunks(build_chunks(call))

    return call_repository, patient_repository, chunk_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container()
    yield
