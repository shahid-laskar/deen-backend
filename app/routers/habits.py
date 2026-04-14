"""
Habits Router — Phase 4
All v1 endpoints preserved + dhikr counter + library + analytics + checklists.
"""
from datetime import date, timedelta, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.core.dependencies import CurrentUser, DB
from app.repositories import HabitRepo, HabitLogRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    HabitLogCreate, HabitLogResponse,
    HabitCreateV2, HabitResponseV2, HabitWithStreakV2, HabitUpdateV2,
    ChecklistItemCreate, ChecklistItemResponse,
    DhikrSessionCreate, DhikrSessionResponse, DhikrIncrementRequest,
    HabitAnalyticsResponse, WeeklyReviewResponse, HabitLibraryItem,
)

router       = APIRouter(prefix="/habits", tags=["habits"])
dhikr_router = APIRouter(prefix="/dhikr",  tags=["dhikr"])


def _streak(logs, target_count):
    complete = {l.log_date for l in logs if l.completed or l.count >= target_count}
    if not complete:
        return {"current_streak": 0, "longest_streak": 0}
    today = date.today()
    cur, chk = 0, today
    while chk in complete:
        cur += 1; chk -= timedelta(days=1)
    if today not in complete:
        cur, chk = 0, today - timedelta(days=1)
        while chk in complete:
            cur += 1; chk -= timedelta(days=1)
    s = sorted(complete); lng, run = 1, 1
    for i in range(1, len(s)):
        run = run + 1 if (s[i] - s[i-1]).days == 1 else 1
        lng = max(lng, run)
    return {"current_streak": cur, "longest_streak": lng}


def _enrich(habit, logs, today=None):
    today = today or date.today()
    sd = _streak(logs, habit.target_count)
    today_log = next((l for l in logs if l.log_date == today), None)
    last30 = [l for l in logs if l.log_date >= today - timedelta(days=30)]
    rate30 = round(len({l.log_date for l in last30 if l.completed}) / 30 * 100, 1)
    base = HabitResponseV2.model_validate(habit).model_dump()
    base.pop("current_streak", None)
    base.pop("longest_streak", None)
    return HabitWithStreakV2(
        **base,
        current_streak=sd["current_streak"],
        longest_streak=sd["longest_streak"],
        completed_today=bool(today_log and today_log.completed),
        completion_rate_30d=rate30,
    )


@router.get("", response_model=list[HabitWithStreakV2])
async def list_habits(current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo, include_archived: bool = False):
    habits = await habit_repo.get_all_for_user(current_user.id, include_archived=include_archived)
    habits.sort(key=lambda h: getattr(h, "habit_stack_order", 0))
    today = date.today()
    return [_enrich(h, await habit_log_repo.get_for_habit(h.id, days=90), today) for h in habits]


@router.post("", response_model=HabitResponseV2, status_code=201)
async def create_habit(payload: HabitCreateV2, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    habit = await habit_repo.create(user_id=current_user.id, **payload.model_dump())
    return HabitResponseV2.model_validate(habit)


@router.get("/library", response_model=list[HabitLibraryItem])
async def get_library(category: Optional[str] = None, difficulty: Optional[str] = None, habit_type: Optional[str] = None):
    from app.services.habit_library import HABIT_LIBRARY
    items = HABIT_LIBRARY
    if category:   items = [h for h in items if h["category"]  == category]
    if difficulty: items = [h for h in items if h["difficulty"] == difficulty]
    if habit_type: items = [h for h in items if h["habit_type"] == habit_type]
    return [HabitLibraryItem(**h) for h in items]


@router.post("/from-library", response_model=HabitResponseV2, status_code=201)
async def add_from_library(current_user: CurrentUser, db: DB, habit_repo: HabitRepo, key: str = Query(...)):
    from app.services.habit_library import HABIT_LIBRARY
    template = next((h for h in HABIT_LIBRARY if h["key"] == key), None)
    if not template:
        raise HTTPException(404, f"Library habit '{key}' not found.")
    data = {k: v for k, v in template.items() if k not in ("key", "estimated_minutes", "description")}
    habit = await habit_repo.create(user_id=current_user.id, is_preset=True, is_active=True, **data)
    return HabitResponseV2.model_validate(habit)


@router.get("/analytics/weekly", response_model=WeeklyReviewResponse)
async def weekly_review(current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habits = await habit_repo.get_all_for_user(current_user.id)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end   = week_start + timedelta(days=6)
    per_habit: dict[str, dict] = {}
    for habit in habits:
        logs = await habit_log_repo.get_for_habit(habit.id, days=14)
        week_logs = [l for l in logs if week_start <= l.log_date <= today]
        completed = len([l for l in week_logs if l.completed])
        possible  = (today - week_start).days + 1
        per_habit[habit.name] = {"completed": completed, "possible": possible, "streak": (habit.current_streak or 0)}
    tp = sum(v["possible"] for v in per_habit.values())
    tc = sum(v["completed"] for v in per_habit.values())
    rate = round((tc / max(tp, 1)) * 100, 1)
    sorted_h = sorted(per_habit.items(), key=lambda x: x[1]["completed"] / max(x[1]["possible"], 1), reverse=True)
    top3   = [h[0] for h in sorted_h[:3]]
    worst1 = [h[0] for h in sorted_h[-1:] if h[1]["completed"] < h[1]["possible"]]
    avg_streak = sum(v["streak"] for v in per_habit.values()) / max(len(per_habit), 1)
    cats = len({h.category for h in habits})
    health = round(0.4*rate + 0.3*min(avg_streak/30*100,100) + 0.3*min(cats/5*100,100), 1)
    return WeeklyReviewResponse(
        week_start=week_start, week_end=week_end, total_habits=len(habits),
        total_possible=tp, total_completed=tc, completion_rate=rate,
        top_habits=top3, needs_attention=worst1,
        streak_summary={h.name: h.current_streak or 0 for h in habits},
        habit_health_score=min(health, 100.0),
    )


@router.get("/analytics/health")
async def habit_health_score(current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habits = await habit_repo.get_all_for_user(current_user.id)
    if not habits:
        return {"score": 0, "label": "No habits yet", "breakdown": {}}
    rates = []
    for h in habits:
        logs = await habit_log_repo.get_for_habit(h.id, days=30)
        last30 = [l for l in logs if l.log_date >= date.today() - timedelta(days=30)]
        rates.append(round(len({l.log_date for l in last30 if l.completed}) / 30 * 100, 1))
    avg_rate   = sum(rates) / len(rates)
    avg_streak = sum(h.current_streak or 0 for h in habits) / len(habits)
    cats       = len({h.category for h in habits})
    score      = round(0.5*avg_rate + 0.3*min(avg_streak/30*100,100) + 0.2*min(cats/5*100,100), 1)
    label      = "Excellent" if score>=85 else "Good" if score>=65 else "Building" if score>=40 else "Getting started"
    return {"score": min(score, 100.0), "label": label, "breakdown": {"completion_rate": avg_rate, "avg_streak": round(avg_streak,1), "category_variety": cats}}


@router.post("/log", response_model=HabitLogResponse, status_code=201)
async def log_habit(payload: HabitLogCreate, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit = await habit_repo.get_owned_or_404(payload.habit_id, current_user.id)
    log = await habit_log_repo.upsert(habit_id=habit.id, user_id=current_user.id, log_date=payload.log_date, count=payload.count, completed=payload.completed, notes=payload.notes)
    logs = await habit_log_repo.get_for_habit(habit.id, days=365)
    sd = _streak(logs, habit.target_count)
    total = len([l for l in logs if l.completed])
    new_tokens = habit.rahmah_tokens or 0
    if total > 0 and total % 30 == 0:
        new_tokens = min(new_tokens + 1, 3)
    await habit_repo.update(habit, current_streak=sd["current_streak"], longest_streak=max(habit.longest_streak or 0, sd["longest_streak"]), total_completions=total, rahmah_tokens=new_tokens)
    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}", response_model=HabitWithStreakV2)
async def get_habit(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    logs = await habit_log_repo.get_for_habit(habit.id, days=90)
    return _enrich(habit, logs)


@router.patch("/{habit_id}", response_model=HabitResponseV2)
async def update_habit(habit_id: UUID, payload: HabitUpdateV2, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    return HabitResponseV2.model_validate(await habit_repo.update(habit, **payload.model_dump(exclude_none=True)))


@router.delete("/{habit_id}", response_model=MessageResponse)
async def delete_habit(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    await habit_repo.delete(await habit_repo.get_owned_or_404(habit_id, current_user.id))
    return MessageResponse(message="Habit deleted.")


@router.post("/{habit_id}/reorder", response_model=HabitResponseV2)
async def reorder_habit(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, order: int = Query(..., ge=0)):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    return HabitResponseV2.model_validate(await habit_repo.update(habit, habit_stack_order=order))


@router.post("/{habit_id}/use-token", response_model=HabitResponseV2)
async def use_rahmah_token(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    tokens = habit.rahmah_tokens or 0
    if tokens < 1:
        raise HTTPException(400, "No Rahmah Tokens available.")
    yesterday = date.today() - timedelta(days=1)
    await habit_log_repo.upsert(habit_id=habit.id, user_id=current_user.id, log_date=yesterday, count=1, completed=True, notes="Rahmah Token used")
    return HabitResponseV2.model_validate(await habit_repo.update(habit, rahmah_tokens=tokens - 1))


@router.get("/{habit_id}/logs", response_model=list[HabitLogResponse])
async def get_habit_logs(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo, days: int = Query(default=30, le=365)):
    await habit_repo.get_owned_or_404(habit_id, current_user.id)
    return [HabitLogResponse.model_validate(l) for l in await habit_log_repo.get_for_habit(habit_id, days=days)]


@router.get("/{habit_id}/analytics", response_model=HabitAnalyticsResponse)
async def get_habit_analytics(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo, habit_log_repo: HabitLogRepo):
    habit   = await habit_repo.get_owned_or_404(habit_id, current_user.id)
    logs365 = await habit_log_repo.get_for_habit(habit.id, days=365)
    logs30  = [l for l in logs365 if l.log_date >= date.today() - timedelta(days=30)]
    logs7   = [l for l in logs365 if l.log_date >= date.today() - timedelta(days=7)]
    sd = _streak(logs365, habit.target_count)
    by_date = {l.log_date: l for l in logs365}
    start = date.today() - timedelta(days=364)
    heatmap = [{"date": str(start+timedelta(days=i)), "completed": bool((lx:=by_date.get(start+timedelta(days=i))) and lx.completed), "count": lx.count if lx else 0} for i in range(365)]
    dow: dict[int, list[bool]] = {i: [] for i in range(7)}
    for l in logs365:
        dow[l.log_date.weekday()].append(l.completed)
    dow_rates = {k: round(sum(v)/len(v)*100, 1) if v else 0.0 for k, v in dow.items()}
    return HabitAnalyticsResponse(
        habit_id=habit.id, habit_name=habit.name, total_logs=len(logs365),
        completion_rate_30d=round(len({l.log_date for l in logs30 if l.completed})/30*100, 1),
        completion_rate_7d=round(len({l.log_date for l in logs7 if l.completed})/7*100, 1),
        best_streak=sd["longest_streak"], current_streak=sd["current_streak"],
        heatmap=heatmap, day_of_week_rates=dow_rates,
    )


@router.get("/{habit_id}/checklist", response_model=list[ChecklistItemResponse])
async def list_checklist(habit_id: UUID, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    await habit_repo.get_owned_or_404(habit_id, current_user.id)
    from app.models.habit import HabitChecklistItem
    r = await db.execute(select(HabitChecklistItem).where(HabitChecklistItem.habit_id == habit_id).order_by(HabitChecklistItem.sort_order))
    return [ChecklistItemResponse.model_validate(i) for i in r.scalars().all()]


@router.post("/{habit_id}/checklist", response_model=ChecklistItemResponse, status_code=201)
async def add_checklist_item(habit_id: UUID, payload: ChecklistItemCreate, current_user: CurrentUser, db: DB, habit_repo: HabitRepo):
    await habit_repo.get_owned_or_404(habit_id, current_user.id)
    from app.models.habit import HabitChecklistItem
    item = HabitChecklistItem(habit_id=habit_id, user_id=current_user.id, **payload.model_dump())
    db.add(item); await db.flush(); await db.refresh(item)
    return ChecklistItemResponse.model_validate(item)


@router.delete("/{habit_id}/checklist/{item_id}", response_model=MessageResponse)
async def delete_checklist_item(habit_id: UUID, item_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.habit import HabitChecklistItem
    r = await db.execute(select(HabitChecklistItem).where(HabitChecklistItem.id == item_id, HabitChecklistItem.user_id == current_user.id))
    item = r.scalar_one_or_none()
    if not item: raise HTTPException(404, "Item not found.")
    await db.delete(item)
    return MessageResponse(message="Deleted.")


@router.post("/{habit_id}/checklist/{item_id}/log", response_model=MessageResponse)
async def toggle_checklist_item(habit_id: UUID, item_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.habit import HabitChecklistLog
    r = await db.execute(select(HabitChecklistLog).where(HabitChecklistLog.item_id == item_id, HabitChecklistLog.log_date == date.today()))
    ex = r.scalar_one_or_none()
    if ex:
        ex.completed = not ex.completed; await db.flush()
    else:
        db.add(HabitChecklistLog(item_id=item_id, user_id=current_user.id, log_date=date.today(), completed=True)); await db.flush()
    return MessageResponse(message="Toggled.")


# ─── Dhikr ───────────────────────────────────────────────────────────────────

@dhikr_router.get("/presets")
async def dhikr_presets():
    from app.services.habit_library import DHIKR_PRESETS
    return DHIKR_PRESETS


@dhikr_router.get("/sessions", response_model=list[DhikrSessionResponse])
async def list_dhikr_sessions(current_user: CurrentUser, db: DB, days: int = Query(default=7, le=30)):
    from app.models.habit import DhikrSession
    start = date.today() - timedelta(days=days)
    r = await db.execute(select(DhikrSession).where(DhikrSession.user_id == current_user.id, DhikrSession.session_date >= start).order_by(DhikrSession.created_at.desc()))
    return [DhikrSessionResponse.model_validate(s) for s in r.scalars().all()]


@dhikr_router.post("/sessions", response_model=DhikrSessionResponse, status_code=201)
async def start_dhikr_session(payload: DhikrSessionCreate, current_user: CurrentUser, db: DB):
    from app.models.habit import DhikrSession
    s = DhikrSession(user_id=current_user.id, session_date=date.today(), dhikr_type=payload.dhikr_type, target_count=payload.target_count, custom_label=payload.custom_label, current_count=0)
    db.add(s); await db.flush(); await db.refresh(s)
    return DhikrSessionResponse.model_validate(s)


@dhikr_router.post("/sessions/{session_id}/increment", response_model=DhikrSessionResponse)
async def increment_dhikr(session_id: UUID, payload: DhikrIncrementRequest, current_user: CurrentUser, db: DB):
    from app.models.habit import DhikrSession
    r = await db.execute(select(DhikrSession).where(DhikrSession.id == session_id, DhikrSession.user_id == current_user.id))
    s = r.scalar_one_or_none()
    if not s: raise HTTPException(404, "Session not found.")
    s.current_count = min(s.current_count + payload.increment, s.target_count)
    if s.current_count >= s.target_count and not s.is_completed:
        s.is_completed = True; s.completed_at = datetime.utcnow().isoformat()
    await db.flush(); await db.refresh(s)
    return DhikrSessionResponse.model_validate(s)


@dhikr_router.post("/sessions/{session_id}/complete", response_model=DhikrSessionResponse)
async def complete_dhikr(session_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.habit import DhikrSession
    r = await db.execute(select(DhikrSession).where(DhikrSession.id == session_id, DhikrSession.user_id == current_user.id))
    s = r.scalar_one_or_none()
    if not s: raise HTTPException(404, "Session not found.")
    s.is_completed = True; s.completed_at = datetime.utcnow().isoformat()
    await db.flush(); await db.refresh(s)
    return DhikrSessionResponse.model_validate(s)


@dhikr_router.get("/history")
async def dhikr_history(current_user: CurrentUser, db: DB, days: int = Query(default=30, le=90)):
    from app.models.habit import DhikrSession
    start = date.today() - timedelta(days=days)
    r = await db.execute(
        select(DhikrSession.dhikr_type, func.sum(DhikrSession.current_count).label("total"), func.count().label("sessions"))
        .where(DhikrSession.user_id == current_user.id, DhikrSession.session_date >= start)
        .group_by(DhikrSession.dhikr_type)
    )
    return [{"dhikr_type": row.dhikr_type, "total_count": int(row.total or 0), "sessions": row.sessions} for row in r.all()]
