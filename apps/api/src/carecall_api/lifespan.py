from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from carecall_application.use_cases import AskQuestionUseCase, GetCallUseCase, ListCallsUseCase
from carecall_llm.grounding import HeuristicAnswerabilityGate
from carecall_llm.providers import MockAnswerGenerator, OpenAIAnswerGenerator
from carecall_persistence.in_memory import (
    InMemoryCallRepository,
    InMemoryChunkRepository,
    InMemoryPatientRepository,
    load_calls_from_json,
)
from carecall_retrieval import HybridRetriever, build_chunks

from . import config


@dataclass
class Container:
    call_repository: InMemoryCallRepository
    patient_repository: InMemoryPatientRepository
    chunk_repository: InMemoryChunkRepository
    ask_question: AskQuestionUseCase
    list_calls: ListCallsUseCase
    get_call: GetCallUseCase


def build_container() -> Container:
    """Wires concrete implementations into the application layer's ports.
    This is the one place that knows about storage mode / answer mode /
    retrieval tuning - swapping demo mode for production-like mode (or mock
    for OpenAI) only ever touches this function."""
    calls = load_calls_from_json(config.TRANSCRIPTS_PATH)

    call_repository = InMemoryCallRepository(calls)
    patient_repository = InMemoryPatientRepository(calls)

    chunks = [chunk for call in calls for chunk in build_chunks(call)]
    chunk_repository = InMemoryChunkRepository(chunks)

    retrieval_service = HybridRetriever(
        chunk_repository.all_chunks(),
        lexical_weight=config.LEXICAL_WEIGHT,
        semantic_weight=config.SEMANTIC_WEIGHT,
        min_relevance_score=config.MIN_RELEVANCE_SCORE,
        default_top_k=config.TOP_K,
    )

    if config.ANSWER_MODE == 'openai' and config.OPENAI_API_KEY:
        answer_generator = OpenAIAnswerGenerator(api_key=config.OPENAI_API_KEY, model=config.OPENAI_CHAT_MODEL)
    else:
        answer_generator = MockAnswerGenerator()

    answerability_gate = HeuristicAnswerabilityGate()

    ask_question = AskQuestionUseCase(
        retrieval_service, answer_generator, answerability_gate, default_limit=config.TOP_K,
    )

    return Container(
        call_repository=call_repository,
        patient_repository=patient_repository,
        chunk_repository=chunk_repository,
        ask_question=ask_question,
        list_calls=ListCallsUseCase(call_repository),
        get_call=GetCallUseCase(call_repository),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container()
    yield
