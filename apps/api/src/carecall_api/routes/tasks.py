from typing import Dict, List, Optional

from carecall_domain import (
    CoordinatorTask,
    InvalidTaskFieldError,
    InvalidTaskStatusTransitionError,
    TaskActivity,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()

# No real identity/auth system yet (see Phase 10 / roles-and-privacy) - the
# actor is a free-text field the frontend's local role/user switcher fills
# in, never a fabricated user record.
DEFAULT_ACTOR = "coordinator"


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    priority: str = "normal"
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    source_event_id: Optional[str] = None
    source_call_id: Optional[str] = None
    source_turn_start: Optional[int] = None
    source_turn_end: Optional[int] = None
    created_by: str = DEFAULT_ACTOR


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    actor: str = DEFAULT_ACTOR


class ActorRequest(BaseModel):
    actor: str = DEFAULT_ACTOR
    note: Optional[str] = None


def _serialize_task(task: CoordinatorTask) -> Dict[str, object]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "patient_id": task.patient_id,
        "priority": task.priority,
        "status": task.status,
        "category": task.category,
        "is_suggested": task.is_suggested,
        "created_by": task.created_by,
        "source_event_id": task.source_event_id,
        "source_call_id": task.source_call_id,
        "source_turn_start": task.source_turn_start,
        "source_turn_end": task.source_turn_end,
        "assignee": task.assignee,
        "due_date": task.due_date,
        "completed_at": task.completed_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _serialize_activity(activity: TaskActivity) -> Dict[str, object]:
    return {
        "activity_id": activity.activity_id,
        "task_id": activity.task_id,
        "action": activity.action,
        "actor": activity.actor,
        "from_status": activity.from_status,
        "to_status": activity.to_status,
        "note": activity.note,
        "created_at": activity.created_at,
    }


@router.get("/api/v1/tasks")
def list_tasks(
    request: Request,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    assignee: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    tasks: List[CoordinatorTask] = container.list_tasks.execute(
        patient_id=patient_id, status=status, priority=priority, category=category, assignee=assignee,
    )
    return {"tasks": [_serialize_task(t) for t in tasks]}


@router.post("/api/v1/tasks", status_code=201, dependencies=[Depends(require_permission("manage_tasks"))])
def create_task(payload: CreateTaskRequest, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        task = container.create_task.execute(
            title=payload.title,
            description=payload.description,
            patient_id=payload.patient_id,
            priority=payload.priority,
            category=payload.category,
            created_by=payload.created_by,
            source_event_id=payload.source_event_id,
            source_call_id=payload.source_call_id,
            source_turn_start=payload.source_turn_start,
            source_turn_end=payload.source_turn_end,
            assignee=payload.assignee,
            due_date=payload.due_date,
            is_suggested=False,
        )
    except InvalidTaskFieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_task(task)


@router.get("/api/v1/tasks/{task_id}")
def get_task(task_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    result = container.get_task.execute(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task, activity = result
    return {"task": _serialize_task(task), "activity": [_serialize_activity(a) for a in activity]}


@router.patch("/api/v1/tasks/{task_id}", dependencies=[Depends(require_permission("manage_tasks"))])
def update_task(task_id: str, payload: UpdateTaskRequest, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        updated = container.update_task.execute(
            task_id,
            actor=payload.actor,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            category=payload.category,
            assignee=payload.assignee,
            due_date=payload.due_date,
            status=payload.status,
            note=payload.note,
        )
    except (InvalidTaskFieldError, InvalidTaskStatusTransitionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(updated)


@router.post("/api/v1/tasks/{task_id}/complete", dependencies=[Depends(require_permission("manage_tasks"))])
def complete_task(task_id: str, request: Request, payload: Optional[ActorRequest] = None) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    payload = payload or ActorRequest()
    try:
        updated = container.update_task.execute(
            task_id, actor=payload.actor, status="completed", note=payload.note,
        )
    except InvalidTaskStatusTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(updated)


@router.post("/api/v1/tasks/{task_id}/reopen", dependencies=[Depends(require_permission("manage_tasks"))])
def reopen_task(task_id: str, request: Request, payload: Optional[ActorRequest] = None) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    payload = payload or ActorRequest()
    try:
        updated = container.update_task.execute(
            task_id, actor=payload.actor, status="open", note=payload.note,
        )
    except InvalidTaskStatusTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(updated)


@router.post("/api/v1/timeline-events/{event_id}/suggest-task", dependencies=[Depends(require_permission("manage_tasks"))])
def suggest_task(event_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    event = container.timeline_event_repository.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    task = container.suggest_task_from_event.execute(event_id)
    if task is None:
        raise HTTPException(status_code=422, detail="This event type does not support a task suggestion")
    return _serialize_task(task)
