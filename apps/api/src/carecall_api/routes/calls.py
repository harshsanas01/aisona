from typing import Dict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get('/api/calls')
def list_calls(request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    calls = container.list_calls.execute()
    return {'calls': [
        {'call_id': call.call_id, 'date': call.date, 'patient_name': call.patient.name}
        for call in calls
    ]}


@router.get('/api/calls/{call_id}')
def get_call(call_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    call = container.get_call.execute(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail='Call not found')
    return {
        'call_id': call.call_id,
        'date': call.date,
        'patient': {'id': call.patient.id, 'name': call.patient.name, 'age': call.patient.age},
        'duration_seconds': call.duration_seconds,
        'turns': [
            {'turn_number': idx + 1, 'speaker': turn.speaker, 'text': turn.text}
            for idx, turn in enumerate(call.turns)
        ],
    }
