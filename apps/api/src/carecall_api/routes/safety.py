from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get('/api/safety-events')
def list_safety_events(
    request: Request,
    call_id: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    events = container.list_safety_events.execute(call_id=call_id, category=category)
    return {'safety_events': [
        {
            'category': e.category,
            'severity': e.severity,
            'call_id': e.call_id,
            'turn_number': e.turn_number,
            'matched_text': e.matched_text,
            'explanation': e.explanation,
            'classifier_type': e.classifier_type,
        }
        for e in events
    ]}
