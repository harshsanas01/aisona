from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict

from carecall_application.ports.brief_prose_generator import BriefProseGenerator
from carecall_application.ports.repositories import (
    BriefRepository,
    CallRepository,
    ChunkRepository,
    CoordinatorTaskRepository,
    FeedbackRepository,
    PatientRepository,
    PatternRepository,
    PersonMentionRepository,
    QuestionAuditRepository,
    TaskActivityRepository,
    TimelineEventRepository,
)
from carecall_application.use_cases import (
    AskQuestionUseCase,
    CompareRetrievalModesUseCase,
    CreateTaskUseCase,
    GenerateBriefUseCase,
    GetBriefUseCase,
    GetCallUseCase,
    GetFeedbackSummaryUseCase,
    GetPatientPatternsUseCase,
    GetPatientPersonMentionsUseCase,
    GetPatientTimelineUseCase,
    GetPatientUseCase,
    GetQuestionAuditUseCase,
    GetTaskUseCase,
    IngestCallUseCase,
    ListBriefsUseCase,
    ListCallsUseCase,
    ListFeedbackUseCase,
    ListPatientsUseCase,
    ListQuestionAuditUseCase,
    ListSafetyEventsUseCase,
    ListTasksUseCase,
    RebuildPatientPatternsUseCase,
    RebuildPatientPersonMentionsUseCase,
    RebuildPatientTimelineUseCase,
    RecordQuestionAuditUseCase,
    RegenerateBriefUseCase,
    SubmitFeedbackUseCase,
    SuggestTaskFromEventUseCase,
    UpdatePatternUseCase,
    UpdatePersonMentionUseCase,
    UpdateTaskUseCase,
    UpdateTimelineEventUseCase,
)
from carecall_domain import (
    DeterministicBriefGenerator,
    DeterministicPatternDetector,
    DeterministicPersonMentionExtractor,
    DeterministicSafetyClassifier,
    DeterministicTimelineExtractor,
)
from carecall_llm.grounding import (
    DeterministicSupportValidator,
    HeuristicAnswerabilityGate,
    StructuralCitationValidator,
)
from carecall_llm.providers import (
    MockAnswerGenerator,
    MockBriefProseGenerator,
    OpenAIAnswerGenerator,
)
from carecall_persistence.in_memory import (
    InMemoryBriefRepository,
    InMemoryCallRepository,
    InMemoryChunkRepository,
    InMemoryCoordinatorTaskRepository,
    InMemoryFeedbackRepository,
    InMemoryPatientRepository,
    InMemoryPatternRepository,
    InMemoryPersonMentionRepository,
    InMemoryQuestionAuditRepository,
    InMemoryTaskActivityRepository,
    InMemoryTimelineEventRepository,
    load_calls_from_json,
)
from carecall_retrieval import HybridRetriever, build_chunks
from fastapi import FastAPI

from . import config


@dataclass
class _Repositories:
    call: CallRepository
    patient: PatientRepository
    chunk: ChunkRepository
    timeline_event: TimelineEventRepository
    pattern: PatternRepository
    task: CoordinatorTaskRepository
    task_activity: TaskActivityRepository
    brief: BriefRepository
    question_audit: QuestionAuditRepository
    feedback: FeedbackRepository
    person_mention: PersonMentionRepository


@dataclass
class Container:
    call_repository: CallRepository
    patient_repository: PatientRepository
    chunk_repository: ChunkRepository
    timeline_event_repository: TimelineEventRepository
    pattern_repository: PatternRepository
    task_repository: CoordinatorTaskRepository
    task_activity_repository: TaskActivityRepository
    brief_repository: BriefRepository
    question_audit_repository: QuestionAuditRepository
    feedback_repository: FeedbackRepository
    person_mention_repository: PersonMentionRepository
    ask_question: AskQuestionUseCase
    list_calls: ListCallsUseCase
    get_call: GetCallUseCase
    ingest_call: IngestCallUseCase
    list_patients: ListPatientsUseCase
    list_safety_events: ListSafetyEventsUseCase
    get_patient: GetPatientUseCase
    get_patient_timeline: GetPatientTimelineUseCase
    rebuild_patient_timeline: RebuildPatientTimelineUseCase
    update_timeline_event: UpdateTimelineEventUseCase
    get_patient_patterns: GetPatientPatternsUseCase
    rebuild_patient_patterns: RebuildPatientPatternsUseCase
    update_pattern: UpdatePatternUseCase
    create_task: CreateTaskUseCase
    list_tasks: ListTasksUseCase
    get_task: GetTaskUseCase
    update_task: UpdateTaskUseCase
    suggest_task_from_event: SuggestTaskFromEventUseCase
    generate_brief: GenerateBriefUseCase
    list_briefs: ListBriefsUseCase
    get_brief: GetBriefUseCase
    regenerate_brief: RegenerateBriefUseCase
    brief_prose_generators: Dict[str, BriefProseGenerator]
    record_question_audit: RecordQuestionAuditUseCase
    list_question_audit: ListQuestionAuditUseCase
    get_question_audit: GetQuestionAuditUseCase
    submit_feedback: SubmitFeedbackUseCase
    list_feedback: ListFeedbackUseCase
    get_feedback_summary: GetFeedbackSummaryUseCase
    get_patient_person_mentions: GetPatientPersonMentionsUseCase
    rebuild_patient_person_mentions: RebuildPatientPersonMentionsUseCase
    update_person_mention: UpdatePersonMentionUseCase
    compare_retrieval_modes: CompareRetrievalModesUseCase


def build_container() -> Container:
    """Wires concrete implementations into the application layer's ports.
    This is the one place that knows about storage mode / answer mode /
    retrieval tuning - swapping demo mode for production-like mode (or mock
    for OpenAI) only ever touches this function."""
    repos = _build_postgres_repositories() if config.STORAGE_MODE == "postgres" else _build_memory_repositories()
    call_repository = repos.call
    patient_repository = repos.patient
    chunk_repository = repos.chunk
    timeline_event_repository = repos.timeline_event
    pattern_repository = repos.pattern
    task_repository = repos.task
    task_activity_repository = repos.task_activity
    brief_repository = repos.brief
    question_audit_repository = repos.question_audit
    feedback_repository = repos.feedback
    person_mention_repository = repos.person_mention

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

    if config.EXTRACTION_MODE == "openai" and config.OPENAI_API_KEY:
        from carecall_llm.extraction import OpenAITimelineExtractor

        timeline_extractor = OpenAITimelineExtractor(api_key=config.OPENAI_API_KEY, model=config.OPENAI_CHAT_MODEL)
    else:
        timeline_extractor = DeterministicTimelineExtractor()

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

    rebuild_patient_timeline = RebuildPatientTimelineUseCase(
        call_repository, timeline_event_repository, timeline_extractor,
    )
    rebuild_patient_patterns = RebuildPatientPatternsUseCase(
        timeline_event_repository, pattern_repository, DeterministicPatternDetector(),
    )
    rebuild_patient_person_mentions = RebuildPatientPersonMentionsUseCase(
        call_repository, person_mention_repository, DeterministicPersonMentionExtractor(),
    )
    # Seed the timeline, its detected patterns, and person mentions for every
    # known patient at boot so the demo/first Postgres boot has real data
    # immediately, without requiring a manual rebuild call first. Idempotent
    # - safe to run on every boot.
    for patient in patient_repository.list_patients():
        rebuild_patient_timeline.execute(patient.id)
        rebuild_patient_patterns.execute(patient.id)
        rebuild_patient_person_mentions.execute(patient.id)

    create_task = CreateTaskUseCase(task_repository, task_activity_repository)

    generate_brief = GenerateBriefUseCase(
        patient_repository, timeline_event_repository, pattern_repository, task_repository,
        brief_repository, DeterministicBriefGenerator(),
    )
    brief_prose_generators: Dict[str, BriefProseGenerator] = {"mock": MockBriefProseGenerator()}
    if config.OPENAI_API_KEY:
        from carecall_llm.providers import OpenAIBriefProseGenerator

        brief_prose_generators["openai"] = OpenAIBriefProseGenerator(
            api_key=config.OPENAI_API_KEY, model=config.OPENAI_CHAT_MODEL,
        )

    record_question_audit = RecordQuestionAuditUseCase(
        question_audit_repository, retain_question_preview=config.AUDIT_RETAIN_QUESTION_PREVIEW,
    )

    update_timeline_event = UpdateTimelineEventUseCase(timeline_event_repository)
    update_pattern = UpdatePatternUseCase(pattern_repository)
    update_person_mention = UpdatePersonMentionUseCase(person_mention_repository)
    compare_retrieval_modes = CompareRetrievalModesUseCase(
        chunk_repository,
        lexical_weight=config.LEXICAL_WEIGHT,
        semantic_weight=config.SEMANTIC_WEIGHT,
        min_relevance_score=config.MIN_RELEVANCE_SCORE,
        default_top_k=config.TOP_K,
    )
    submit_feedback = SubmitFeedbackUseCase(
        feedback_repository,
        update_timeline_event=update_timeline_event,
        update_pattern=update_pattern,
        update_person_mention=update_person_mention,
    )

    return Container(
        call_repository=call_repository,
        patient_repository=patient_repository,
        chunk_repository=chunk_repository,
        timeline_event_repository=timeline_event_repository,
        pattern_repository=pattern_repository,
        task_repository=task_repository,
        task_activity_repository=task_activity_repository,
        brief_repository=brief_repository,
        question_audit_repository=question_audit_repository,
        feedback_repository=feedback_repository,
        person_mention_repository=person_mention_repository,
        ask_question=ask_question,
        list_calls=ListCallsUseCase(call_repository),
        get_call=GetCallUseCase(call_repository),
        ingest_call=ingest_call,
        list_patients=ListPatientsUseCase(patient_repository),
        list_safety_events=ListSafetyEventsUseCase(call_repository, DeterministicSafetyClassifier()),
        get_patient=GetPatientUseCase(patient_repository),
        get_patient_timeline=GetPatientTimelineUseCase(timeline_event_repository),
        rebuild_patient_timeline=rebuild_patient_timeline,
        update_timeline_event=update_timeline_event,
        get_patient_patterns=GetPatientPatternsUseCase(pattern_repository),
        rebuild_patient_patterns=rebuild_patient_patterns,
        update_pattern=update_pattern,
        create_task=create_task,
        list_tasks=ListTasksUseCase(task_repository),
        get_task=GetTaskUseCase(task_repository, task_activity_repository),
        update_task=UpdateTaskUseCase(task_repository, task_activity_repository),
        suggest_task_from_event=SuggestTaskFromEventUseCase(timeline_event_repository, task_repository, create_task),
        generate_brief=generate_brief,
        list_briefs=ListBriefsUseCase(brief_repository),
        get_brief=GetBriefUseCase(brief_repository),
        regenerate_brief=RegenerateBriefUseCase(brief_repository, generate_brief),
        brief_prose_generators=brief_prose_generators,
        record_question_audit=record_question_audit,
        list_question_audit=ListQuestionAuditUseCase(question_audit_repository),
        get_question_audit=GetQuestionAuditUseCase(question_audit_repository),
        submit_feedback=submit_feedback,
        list_feedback=ListFeedbackUseCase(feedback_repository),
        get_feedback_summary=GetFeedbackSummaryUseCase(feedback_repository),
        get_patient_person_mentions=GetPatientPersonMentionsUseCase(person_mention_repository),
        rebuild_patient_person_mentions=rebuild_patient_person_mentions,
        update_person_mention=update_person_mention,
        compare_retrieval_modes=compare_retrieval_modes,
    )


def _build_memory_repositories() -> _Repositories:
    calls = load_calls_from_json(config.TRANSCRIPTS_PATH)
    call_repository = InMemoryCallRepository(calls)
    patient_repository = InMemoryPatientRepository(call_repository)
    chunks = [chunk for call in calls for chunk in build_chunks(call)]
    chunk_repository = InMemoryChunkRepository(chunks)
    timeline_event_repository = InMemoryTimelineEventRepository()
    pattern_repository = InMemoryPatternRepository()
    task_repository = InMemoryCoordinatorTaskRepository()
    task_activity_repository = InMemoryTaskActivityRepository()
    brief_repository = InMemoryBriefRepository()
    question_audit_repository = InMemoryQuestionAuditRepository()
    feedback_repository = InMemoryFeedbackRepository()
    person_mention_repository = InMemoryPersonMentionRepository()
    return _Repositories(
        call=call_repository,
        patient=patient_repository,
        chunk=chunk_repository,
        timeline_event=timeline_event_repository,
        pattern=pattern_repository,
        task=task_repository,
        task_activity=task_activity_repository,
        brief=brief_repository,
        question_audit=question_audit_repository,
        feedback=feedback_repository,
        person_mention=person_mention_repository,
    )


def _build_postgres_repositories() -> _Repositories:
    # Imported lazily so sqlalchemy/psycopg/pgvector are only required when
    # CARECALL_STORAGE_MODE=postgres is actually selected - demo mode and
    # unit tests never need them installed.
    from carecall_persistence.postgres import (
        PostgresBriefRepository,
        PostgresCallRepository,
        PostgresChunkRepository,
        PostgresCoordinatorTaskRepository,
        PostgresFeedbackRepository,
        PostgresPatientRepository,
        PostgresPatternRepository,
        PostgresPersonMentionRepository,
        PostgresQuestionAuditRepository,
        PostgresTaskActivityRepository,
        PostgresTimelineEventRepository,
        create_session_factory,
    )

    session_factory = create_session_factory(config.DATABASE_URL)
    call_repository = PostgresCallRepository(session_factory)
    patient_repository = PostgresPatientRepository(session_factory)
    chunk_repository = PostgresChunkRepository(session_factory)
    timeline_event_repository = PostgresTimelineEventRepository(session_factory)
    pattern_repository = PostgresPatternRepository(session_factory)
    task_repository = PostgresCoordinatorTaskRepository(session_factory)
    task_activity_repository = PostgresTaskActivityRepository(session_factory)
    brief_repository = PostgresBriefRepository(session_factory)
    question_audit_repository = PostgresQuestionAuditRepository(session_factory)
    feedback_repository = PostgresFeedbackRepository(session_factory)
    person_mention_repository = PostgresPersonMentionRepository(session_factory)

    # First boot against an empty database: bootstrap from the demo fixture
    # so production-like mode has the same starting corpus as memory mode.
    # Later ingestion (POST /api/calls) adds calls incrementally from here.
    if not call_repository.list_calls():
        for call in load_calls_from_json(config.TRANSCRIPTS_PATH):
            call_repository.add_call(call)
            chunk_repository.add_chunks(build_chunks(call))

    return _Repositories(
        call=call_repository,
        patient=patient_repository,
        chunk=chunk_repository,
        timeline_event=timeline_event_repository,
        pattern=pattern_repository,
        task=task_repository,
        task_activity=task_activity_repository,
        brief=brief_repository,
        question_audit=question_audit_repository,
        feedback=feedback_repository,
        person_mention=person_mention_repository,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container()
    yield
