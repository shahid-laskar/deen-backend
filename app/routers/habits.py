from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import HabitRepo, HabitLogRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    HabitCreate, HabitLogCreate, HabitLogResponse,
    HabitResponse, HabitUpdate, HabitWithStreak,
)

router = APIRouter(prefix="/habits", tags=["habits"])


def _streak(logs, target_count):
    complete_dates = {l.log_date for l in logs if l.completed or l.count >= target_count}
    if not complete_dates:
        return {"current_streak": 0, "longest_streak": 0}
    today = date.today()
    current, check = 0, today
    while check in complete_dates:
        current += 1
        check -= timedelta(days=1)
    if today not in complete_dates:
        current, check = 0, today - timedelta(days=1)
        while check in complete_dates:
            current += 1
            check -= timedelta(days=1)
    sorted_dates = sorted(complete_dates)
    longest, run = 1, 1
    for i in range(1, len(sorted_dates)):
        run = run + 1 if (sorted_dates[i] - sorted_dates[i - 1]).days == 1 else 1
        longest = max(longest, run)
    return {"current_streak": current, "longest_streak": longest}


@router.get("", response_model=list[HabitWithStreak])
async def list_habits(current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo, include_archived: bool = False):
    habits = await habit_repo.get_all_for_user(current_user.id, include_archived=include_archived)
    today = date.today()
    enriched = []
    for habit in habits:
        logs = await habit_log_repo.get_for_habit(habit.id, days=90)
        sd = _streak(logs, habit.target_count)
        today_log = next((l for l in logs if l.log_date == today), None)
        last30 = [l for l in logs if l.log_date >= today - timedelta(days=30)]
        rate30 = round((len({l.log_date for l in last30 if l.completed}) / 30) * 100, 1)
        enriched.append(HabitWithStreak(
            **HabitResponse.model_validate(habit).model_dump(),
            current_streak=sd["current_streak"],
            longest_streak=sd["longest_streak"],
            completed_today=today_log.completed if today_log else False,
            completion_rate_30d=rate30,
        ))
    return enriched


@router.post("", response_model=HabitResponse, status_code=201)
async def create_habit(payload: HabitCreate, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    habit = await habit_repo.create(user_id=current_user.id, **payload.model_dump())
    return HabitResponse.model_validate(habit)


@router.get("/{habit_id}", response_model=HabitWithStreak)
async def get_habit(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    logs = await habit_log_repo.get_for_habit(habit.id, days=90)
    sd = _streak(logs, habit.target_count)
    today_log = next((l for l in logs if l.log_date == date.today()), None)
    return HabitWithStreak(
        **HabitResponse.model_validate(habit).model_dump(),
        current_streak=sd["current_streak"],
        longest_streak=sd["longest_streak"],
        completed_today=today_log.completed if today_log else False,
        completion_rate_30d=0.0,
    )


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(habit_id: UUID, payload: HabitUpdate, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    habit = await habit_repo.update(habit, **payload.model_dump(exclude_none=True))
    return HabitResponse.model_validate(habit)


@router.delete("/{habit_id}", response_model=MessageResponse)
async def delete_habit(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    await habit_repo.delete(habit)
    return MessageResponse(message="Habit deleted.")


@router.post("/log", response_model=HabitLogResponse, status_code=201)
async def log_habit(payload: HabitLogCreate, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit = await habit_repo.get_owned_or_404(payload.habit_id, current_user.id)
    log = await habit_log_repo.upsert(
        habit_id=habit.id,
        user_id=current_user.id,
        log_date=payload.log_date,
        count=payload.count,
        completed=payload.completed,
        notes=payload.notes,
    )
    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}/logs", response_model=list[HabitLogResponse])
async def get_habit_logs(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo, days: int = Query(default=30, le=365)):
    await habit_repo.get_owned_or_404(habit_id, current_user.id)
    logs = await habit_log_repo.get_for_habit(habit_id, days=days)
    return [HabitLogResponse.model_validate(l) for l in logs]
