import json
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from carecall_domain import InvalidDateRangeError

from ..schemas import AskRequest, AskResponse, CitationOut

router = APIRouter()


@router.post('/api/ask', response_model=AskResponse)
def ask(payload: AskRequest, request: Request) -> AskResponse:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=422, detail='Question must not be empty')

    try:
        result = container.ask_question.execute(
            payload.question,
            patient_id=payload.patient_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AskResponse(
        question=result.question,
        answer=result.answer,
        answerable=result.answerable,
        confidence=result.confidence,
        citations=[CitationOut(**asdict(citation)) for citation in result.citations],
        retrieval_debug=result.retrieval_debug,
        filters=result.filters,
    )


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post('/api/ask/stream')
def ask_stream(payload: AskRequest, request: Request) -> StreamingResponse:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=422, detail='Question must not be empty')

    def event_stream():
        try:
            for stream_event in container.ask_question.stream(
                payload.question,
                patient_id=payload.patient_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
            ):
                data = stream_event.data
                if stream_event.event == 'citations':
                    data = {'citations': [asdict(c) for c in data['citations']]}
                yield _format_sse(stream_event.event, data)
        except InvalidDateRangeError as exc:
            yield _format_sse('error', {'detail': str(exc)})

    return StreamingResponse(event_stream(), media_type='text/event-stream')
