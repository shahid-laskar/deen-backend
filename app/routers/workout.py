"""Workout Planner Router"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import WorkoutPlanRepo, WorkoutSessionRepo, ExerciseRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    ExerciseCreate, ExerciseResponse,
    WorkoutPlanCreate, WorkoutPlanResponse, WorkoutPlanUpdate,
    WorkoutSessionCreate, WorkoutSessionResponse, WorkoutSessionUpdate,
)

router = APIRouter(prefix="/workout", tags=["workout"])


@router.get("/plans", response_model=list[WorkoutPlanResponse])
async def list_plans(current_user: CurrentUser, db: DB, repo: WorkoutPlanRepo):
    plans = await repo.get_all_for_user(current_user.id)
    return [WorkoutPlanResponse.model_validate(p) for p in plans]


@router.post("/plans", response_model=WorkoutPlanResponse, status_code=201)
async def create_plan(payload: WorkoutPlanCreate, current_user: CurrentUser, db: DB, repo: WorkoutPlanRepo):
    plan = await repo.create(user_id=current_user.id, **payload.model_dump())
    return WorkoutPlanResponse.model_validate(plan)


@router.patch("/plans/{plan_id}", response_model=WorkoutPlanResponse)
async def update_plan(plan_id: UUID, payload: WorkoutPlanUpdate, current_user: CurrentUser, db: DB, repo: WorkoutPlanRepo):
    plan = await repo.get_owned_or_404(plan_id, current_user.id)
    plan = await repo.update(plan, **payload.model_dump(exclude_none=True))
    return WorkoutPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", response_model=MessageResponse)
async def delete_plan(plan_id: UUID, current_user: CurrentUser, db: DB, repo: WorkoutPlanRepo):
    plan = await repo.get_owned_or_404(plan_id, current_user.id)
    await repo.delete(plan)
    return MessageResponse(message="Workout plan deleted.")


@router.get("/sessions", response_model=list[WorkoutSessionResponse])
async def list_sessions(current_user: CurrentUser, db: DB, repo: WorkoutSessionRepo,
                         start_date: date = Query(default=None), end_date: date = Query(default=None)):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=29))
    sessions = await repo.get_for_user(current_user.id, start=start, end=end)
    return [WorkoutSessionResponse.model_validate(s) for s in sessions]


@router.post("/sessions", response_model=WorkoutSessionResponse, status_code=201)
async def log_session(payload: WorkoutSessionCreate, current_user: CurrentUser, db: DB, repo: WorkoutSessionRepo):
    session = await repo.create(user_id=current_user.id, **payload.model_dump())
    return WorkoutSessionResponse.model_validate(session)


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionResponse)
async def update_session(session_id: UUID, payload: WorkoutSessionUpdate, current_user: CurrentUser, db: DB, repo: WorkoutSessionRepo):
    session = await repo.get_owned_or_404(session_id, current_user.id)
    session = await repo.update(session, **payload.model_dump(exclude_none=True))
    return WorkoutSessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def delete_session(session_id: UUID, current_user: CurrentUser, db: DB, repo: WorkoutSessionRepo):
    session = await repo.get_owned_or_404(session_id, current_user.id)
    await repo.delete(session)
    return MessageResponse(message="Workout session deleted.")


@router.get("/stats")
async def workout_stats(current_user: CurrentUser, db: DB, repo: WorkoutSessionRepo):
    weekly = await repo.get_weekly_count(current_user.id)
    all_sessions = await repo.get_for_user(current_user.id)
    total_minutes = sum(s.duration_minutes or 0 for s in all_sessions)
    return {"sessions_this_week": weekly, "total_sessions": len(all_sessions), "total_minutes": total_minutes}


@router.get("/exercises/search", response_model=list[ExerciseResponse])
async def search_exercises(q: str = Query(min_length=2), current_user: CurrentUser = ...,
                            db: DB = ..., repo: ExerciseRepo = ...):
    exercises = await repo.search(current_user.id, q)
    return [ExerciseResponse.model_validate(e) for e in exercises]


@router.post("/exercises", response_model=ExerciseResponse, status_code=201)
async def create_exercise(payload: ExerciseCreate, current_user: CurrentUser, db: DB, repo: ExerciseRepo):
    exercise = await repo.create(user_id=current_user.id, **payload.model_dump())
    return ExerciseResponse.model_validate(exercise)
