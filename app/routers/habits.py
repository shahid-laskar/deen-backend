from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, and_

from app.core.dependencies import CurrentUser, DB
from app.models.habit import Habit, HabitLog
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    HabitCreate,
    HabitLogCreate,
    HabitLogResponse,
    HabitResponse,
    HabitUpdate,
    HabitWithStreak,
)

router = APIRouter(prefix="/habits", tags=["habits"])


def _calculate_streak(logs: list[HabitLog], target_count: int) -> dict:
    """Calculate current and longest streak for a habit."""
    complete_dates = {
        log.log_date for log in logs
        if log.completed or log.count >= target_count
    }

    if not complete_dates:
        return {"current_streak": 0, "longest_streak": 0}

    today = date.today()
    current = 0
    check = today
    while check in complete_dates:
        current += 1
        check = check - timedelta(days=1)

    if today not in complete_dates:
        current = 0
        check = today - timedelta(days=1)
        while check in complete_dates:
            current += 1
            check = check - timedelta(days=1)

    sorted_dates = sorted(complete_dates)
    longest, run = 1, 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {"current_streak": current, "longest_streak": longest}


@router.get("", response_model=list[HabitWithStreak])
async def list_habits(current_user: CurrentUser, db: DB, include_archived: bool = False):
    """List all user habits with streak data."""
    query = select(Habit).where(Habit.user_id == current_user.id)
    if not include_archived:
        query = query.where(Habit.is_active == True)
    result = await db.execute(query.order_by(Habit.created_at))
    habits = result.scalars().all()

    today = date.today()
    start_90 = today - timedelta(days=90)
    enriched = []
    for habit in habits:
        log_result = await db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == habit.id,
                HabitLog.log_date >= start_90,
            )
        )
        logs = log_result.scalars().all()
        streak_data = _calculate_streak(logs, habit.target_count)

        today_log = next((l for l in logs if l.log_date == today), None)
        completed_today = today_log.completed if today_log else False

        last_30 = [l for l in logs if l.log_date >= today - timedelta(days=30)]
        complete_30 = len({l.log_date for l in last_30 if l.completed})
        rate_30 = round((complete_30 / 30) * 100, 1)

        enriched.append(HabitWithStreak(
            **HabitResponse.model_validate(habit).model_dump(),
            current_streak=streak_data["current_streak"],
            longest_streak=streak_data["longest_streak"],
            completed_today=completed_today,
            completion_rate_30d=rate_30,
        ))

    return enriched


@router.post("", response_model=HabitResponse, status_code=201)
async def create_habit(payload: HabitCreate, current_user: CurrentUser, db: DB):
    """Create a new habit."""
    habit = Habit(user_id=current_user.id, **payload.model_dump())
    db.add(habit)
    await db.flush()
    await db.refresh(habit)
    return HabitResponse.model_validate(habit)


@router.get("/{habit_id}", response_model=HabitWithStreak)
async def get_habit(habit_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")

    log_result = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == habit.id,
            HabitLog.log_date >= date.today() - timedelta(days=90),
        )
    )
    logs = log_result.scalars().all()
    streak_data = _calculate_streak(logs, habit.target_count)
    today_log = next((l for l in logs if l.log_date == date.today()), None)

    return HabitWithStreak(
        **HabitResponse.model_validate(habit).model_dump(),
        current_streak=streak_data["current_streak"],
        longest_streak=streak_data["longest_streak"],
        completed_today=today_log.completed if today_log else False,
        completion_rate_30d=0.0,
    )


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(habit_id: UUID, payload: HabitUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(habit, field, value)

    await db.flush()
    await db.refresh(habit)
    return HabitResponse.model_validate(habit)


@router.delete("/{habit_id}", response_model=MessageResponse)
async def delete_habit(habit_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    await db.delete(habit)
    return MessageResponse(message="Habit deleted.")


# ─── Habit Logs ───────────────────────────────────────────────────────────────

@router.post("/log", response_model=HabitLogResponse, status_code=201)
async def log_habit(payload: HabitLogCreate, current_user: CurrentUser, db: DB):
    """Log a habit completion. Upserts if log for this habit+date exists."""
    # Verify ownership
    result = await db.execute(
        select(Habit).where(Habit.id == payload.habit_id, Habit.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Habit not found.")

    existing_result = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == payload.habit_id,
            HabitLog.log_date == payload.log_date,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        log = existing
    else:
        log = HabitLog(user_id=current_user.id, **payload.model_dump())
        db.add(log)

    await db.flush()
    await db.refresh(log)
    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}/logs", response_model=list[HabitLogResponse])
async def get_habit_logs(
    habit_id: UUID,
    current_user: CurrentUser,
    db: DB,
    days: int = Query(default=30, le=365),
):
    """Get habit logs for the last N days."""
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Habit not found.")

    start = date.today() - timedelta(days=days)
    log_result = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == habit_id,
            HabitLog.log_date >= start,
        ).order_by(HabitLog.log_date.desc())
    )
    return [HabitLogResponse.model_validate(l) for l in log_result.scalars().all()]
