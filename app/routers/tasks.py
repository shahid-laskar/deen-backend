from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB
from app.models.task import Task
from app.schemas.base import MessageResponse
from app.schemas.schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser,
    db: DB,
    due_date: date = Query(default=None),
    completed: bool = Query(default=None),
    time_block: str = Query(default=None),
    priority: str = Query(default=None),
):
    """List tasks with optional filters."""
    query = select(Task).where(Task.user_id == current_user.id)
    if due_date:
        query = query.where(Task.due_date == due_date)
    if completed is not None:
        query = query.where(Task.completed == completed)
    if time_block:
        query = query.where(Task.time_block == time_block)
    if priority:
        query = query.where(Task.priority == priority)
    query = query.order_by(Task.sort_order, Task.due_date, Task.created_at)
    result = await db.execute(query)
    return [TaskResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/today", response_model=list[TaskResponse])
async def list_today_tasks(current_user: CurrentUser, db: DB):
    """Get tasks due today, grouped by prayer time-block."""
    today = date.today()
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.due_date == today,
            Task.completed == False,
        ).order_by(Task.sort_order)
    )
    return [TaskResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, current_user: CurrentUser, db: DB):
    task = Task(user_id=current_user.id, **payload.model_dump())
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, payload: TaskUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    # Auto-set completed_at
    if payload.completed is True and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: UUID, current_user: CurrentUser, db: DB):
    """Quick complete a task."""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(task_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    await db.delete(task)
    return MessageResponse(message="Task deleted.")
