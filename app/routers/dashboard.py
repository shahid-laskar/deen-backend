"""
Dashboard Summary Router
========================
GET /dashboard/summary — Single aggregated endpoint replacing 6+ parallel calls.
Designed specifically for mobile app initial load performance.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import PrayerRepo, HabitRepo, HabitLogRepo
from app.schemas.base import AppBaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class PrayerSummaryItem(AppBaseModel):
    total_logged: int
    total_on_time: int
    completion_pct: float


class HabitSummaryItem(AppBaseModel):
    total_habits: int
    completed_today: int
    completion_pct: float
    current_streak: int


class DashboardSummaryResponse(AppBaseModel):
    today_date: str
    prayer: PrayerSummaryItem
    habits: HabitSummaryItem
    tasks_due_today: int
    hifz_due_today: int
    xp_total: int
    level: int
    unread_notifications: int


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: CurrentUser,
    db: DB,
    prayer_repo: PrayerRepo,
    habit_repo: HabitRepo,
    habit_log_repo: HabitLogRepo,
):
    """
    Single aggregated dashboard endpoint for mobile app.
    Replaces parallel calls to /prayer/summary/today, /habits, /tasks/today, etc.
    Target response time: < 300ms.
    """
    today = date.today()
    OBLIGATORY = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

    # ── Prayer summary ────────────────────────────────────────────────────────
    prayer_logs = await prayer_repo.get_for_date_range(current_user.id, today, today)
    obligatory = [l for l in prayer_logs if l.prayer_name in OBLIGATORY]
    prayer_on_time = len([l for l in obligatory if l.status == "on_time"])
    prayer_summary = PrayerSummaryItem(
        total_logged=len(obligatory),
        total_on_time=prayer_on_time,
        completion_pct=round((len(obligatory) / 5) * 100, 1),
    )

    # ── Habit summary ─────────────────────────────────────────────────────────
    habits = await habit_repo.get_all_for_user(current_user.id)
    active_habits = [h for h in habits if h.is_active]
    completed_today_count = 0
    max_streak = 0
    for habit in active_habits:
        logs = await habit_log_repo.get_for_habit(habit.id, days=1)
        today_log = next((l for l in logs if l.log_date == today), None)
        if today_log and today_log.completed:
            completed_today_count += 1
        max_streak = max(max_streak, habit.current_streak or 0)

    habit_summary = HabitSummaryItem(
        total_habits=len(active_habits),
        completed_today=completed_today_count,
        completion_pct=round((completed_today_count / max(len(active_habits), 1)) * 100, 1),
        current_streak=max_streak,
    )

    # ── Tasks due today ───────────────────────────────────────────────────────
    from app.models.task import Task
    from sqlalchemy import select, func as sa_func
    tasks_result = await db.execute(
        select(sa_func.count(Task.id)).where(
            Task.user_id == current_user.id,
            Task.due_date == today,
            Task.completed == False,
        )
    )
    tasks_due = tasks_result.scalar() or 0

    # ── Hifz due today ────────────────────────────────────────────────────────
    from app.models.quran import HifzProgress, HifzStatus
    hifz_result = await db.execute(
        select(sa_func.count(HifzProgress.id)).where(
            HifzProgress.user_id == current_user.id,
            HifzProgress.next_review <= today,
            HifzProgress.status != HifzStatus.MEMORISED,
        )
    )
    hifz_due = hifz_result.scalar() or 0

    # ── Gamification ─────────────────────────────────────────────────────────
    from app.models.gamification import UserXP
    xp_result = await db.execute(
        select(sa_func.sum(UserXP.amount)).where(UserXP.user_id == current_user.id)
    )
    xp_total = int(xp_result.scalar() or 0)
    level = max(1, xp_total // 100)

    return DashboardSummaryResponse(
        today_date=today.isoformat(),
        prayer=prayer_summary,
        habits=habit_summary,
        tasks_due_today=tasks_due,
        hifz_due_today=hifz_due,
        xp_total=xp_total,
        level=level,
        unread_notifications=0,  # Phase 10 — notifications table
    )
