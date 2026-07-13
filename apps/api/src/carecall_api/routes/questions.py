from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

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
