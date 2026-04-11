from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import TaskRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser, db: DB, task_repo: TaskRepo,
    due_date: date = Query(default=None), completed: bool = Query(default=None),
    time_block: str = Query(default=None), priority: str = Query(default=None),
):
    tasks = await task_repo.get_for_user(current_user.id, due_date=due_date, completed=completed, time_block=time_block, priority=priority)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/today", response_model=list[TaskResponse])
async def list_today_tasks(current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    tasks = await task_repo.get_due_today(current_user.id)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    task = await task_repo.create(user_id=current_user.id, **payload.model_dump())
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    task = await task_repo.get_owned_or_404(task_id, current_user.id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, payload: TaskUpdate, current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    task = await task_repo.get_owned_or_404(task_id, current_user.id)
    updates = payload.model_dump(exclude_none=True)
    if updates.get("completed") is True and not task.completed_at:
        updates["completed_at"] = datetime.now(timezone.utc)
    task = await task_repo.update(task, **updates)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: UUID, current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    task = await task_repo.get_owned_or_404(task_id, current_user.id)
    task = await task_repo.update(task, completed=True, completed_at=datetime.now(timezone.utc))
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(task_id: UUID, current_user: CurrentUser, db: DB, task_repo: TaskRepo):
    task = await task_repo.get_owned_or_404(task_id, current_user.id)
    await task_repo.delete(task)
    return MessageResponse(message="Task deleted.")
