from typing import Dict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get('/api/patients')
def list_patients(request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    patients = container.list_patients.execute()
    return {'patients': [
        {'id': patient.id, 'name': patient.name, 'age': patient.age}
        for patient in patients
    ]}
