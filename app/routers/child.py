"""Child Upbringing Router — Phase 1+"""
from datetime import date
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.core.dependencies import CurrentUser, DB
from app.repositories import ChildRepo, MilestoneRepo, DuaTeachingRepo, LessonLogRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    ChildCreate, ChildResponse, ChildUpdate,
    MilestoneCreate, MilestoneResponse, MilestoneUpdate,
    DuaTeachingCreate, DuaTeachingResponse, DuaTeachingUpdate,
    LessonLogCreate, LessonLogResponse,
    ChildActivityLogCreate, ChildActivityLogResponse,
    ChildBadgeResponse, ChildActivityResult,
    ChildStoryProgressResponse, ChildQuranProgressResponse, ChildQuranProgressUpdate,
)

router = APIRouter(prefix="/children", tags=["children"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _recalc_age_group(dob: date | None) -> str | None:
    if not dob:
        return None
    months = (date.today().year - dob.year) * 12 + (date.today().month - dob.month)
    if months < 48:  return "toddler"
    if months < 84:  return "young"
    if months < 120: return "middle"
    if months < 156: return "preteen"
    return "teen"


# ─── Library ─────────────────────────────────────────────────────────────────

@router.get("/milestone-library")
async def get_milestones_library(age_group: str = Query(default=None)):
    from app.services.child_library import get_milestone_library
    return get_milestone_library(age_group)


@router.get("/activity-library")
async def get_activities_library(age_group: str = Query(default=None)):
    from app.services.child_library import get_activity_library
    return get_activity_library(age_group)


@router.get("/story-library")
async def get_stories_library(age_group: str = Query(default=None), category: str = Query(default=None)):
    from app.services.child_stories import get_stories_by_category
    return get_stories_by_category(age_group, category)


@router.get("/story-library/{key}")
async def get_story_detail(key: str):
    from app.services.child_stories import get_story_by_key
    story = get_story_by_key(key)
    if not story:
        raise HTTPException(404, "Story not found")
    return story


@router.get("/badge-library")
async def get_badge_library():
    from app.services.child_gamification import BADGE_DEFINITIONS
    return BADGE_DEFINITIONS


@router.get("/dua-library")
async def get_dua_library(age_group: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    from app.services.child_duas import get_dua_library as get_duas
    return get_duas(age_group, category)


# ─── Children CRUD ───────────────────────────────────────────────────────────

@router.get("", response_model=list[ChildResponse])
async def list_children(current_user: CurrentUser, db: DB, repo: ChildRepo):
    children = await repo.get_all_for_user(current_user.id)
    # Auto-update age_group on fetch
    for child in children:
        computed = _recalc_age_group(child.date_of_birth)
        if computed != child.age_group:
            child.age_group = computed
    await db.flush()
    return [ChildResponse.model_validate(c) for c in children]


@router.post("", response_model=ChildResponse, status_code=201)
async def create_child(payload: ChildCreate, current_user: CurrentUser, db: DB, repo: ChildRepo):
    data = payload.model_dump()
    data["age_group"] = _recalc_age_group(data.get("date_of_birth"))
    child = await repo.create(user_id=current_user.id, **data)
    return ChildResponse.model_validate(child)


@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.get_owned_or_404(child_id, current_user.id)
    child.age_group = _recalc_age_group(child.date_of_birth)
    await db.flush()
    return ChildResponse.model_validate(child)


@router.patch("/{child_id}", response_model=ChildResponse)
async def update_child(child_id: UUID, payload: ChildUpdate, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.get_owned_or_404(child_id, current_user.id)
    update_data = payload.model_dump(exclude_none=True)
    if "date_of_birth" in update_data:
        update_data["age_group"] = _recalc_age_group(update_data["date_of_birth"])
    child = await repo.update(child, **update_data)
    return ChildResponse.model_validate(child)


@router.delete("/{child_id}", response_model=MessageResponse)
async def delete_child(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.get_owned_or_404(child_id, current_user.id)
    await repo.delete(child)
    return MessageResponse(message="Child profile deleted.")


# ─── Milestones ──────────────────────────────────────────────────────────────

@router.get("/{child_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(child_id: UUID, current_user: CurrentUser, db: DB, repo: MilestoneRepo,
                           category: str = Query(default=None)):
    milestones = await repo.get_for_child(child_id, category=category)
    return [MilestoneResponse.model_validate(m) for m in milestones]


@router.post("/{child_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def create_milestone(child_id: UUID, payload: MilestoneCreate, current_user: CurrentUser,
                            db: DB, repo: MilestoneRepo):
    milestone = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())
    return MilestoneResponse.model_validate(milestone)


@router.post("/{child_id}/milestones/from-library", response_model=MilestoneResponse, status_code=201)
async def create_milestone_from_library(
    child_id: UUID, current_user: CurrentUser, db: DB, repo: MilestoneRepo,
    key: str = Query(...)
):
    from app.services.child_library import get_milestone_library
    
    # Check if already seeded
    existing = await repo.get_for_child(child_id)
    if any(m.title == key for m in existing):  # simple check; ideally we'd have a key field, but we can match title
        raise HTTPException(400, "Milestone already added")
        
    lib = get_milestone_library()
    item = next((m for m in lib if m["key"] == key), None)
    if not item:
        raise HTTPException(404, "Milestone not found in library")
        
    ms = await repo.create(
        child_id=child_id, user_id=current_user.id,
        title=item["title"], description=item.get("description"),
        category=item["category"], target_age_months=item.get("target_age_months"),
        is_template=True
    )
    return MilestoneResponse.model_validate(ms)


@router.post("/{child_id}/milestones/seed-age-group", response_model=list[MilestoneResponse], status_code=201)
async def seed_milestones_for_age(
    child_id: UUID, current_user: CurrentUser, db: DB, repo: MilestoneRepo, child_repo: ChildRepo
):
    from app.services.child_library import get_milestone_library
    child = await child_repo.get_owned_or_404(child_id, current_user.id)
    if not child.age_group:
        raise HTTPException(400, "Child does not have an age_group set.")
        
    lib = get_milestone_library(child.age_group)
    existing = {m.title for m in await repo.get_for_child(child_id)}
    
    added = []
    for item in lib:
        if item["title"] not in existing:
            ms = await repo.create(
                child_id=child_id, user_id=current_user.id,
                title=item["title"], description=item.get("description"),
                category=item["category"], target_age_months=item.get("target_age_months"),
                is_template=True
            )
            added.append(ms)
            
    return [MilestoneResponse.model_validate(m) for m in added]


@router.patch("/{child_id}/milestones/{ms_id}", response_model=MilestoneResponse)
async def update_milestone(child_id: UUID, ms_id: UUID, payload: MilestoneUpdate,
                            current_user: CurrentUser, db: DB, repo: MilestoneRepo):
    ms = await repo.get_owned_or_404(ms_id, current_user.id)
    ms = await repo.update(ms, **payload.model_dump(exclude_none=True))
    return MilestoneResponse.model_validate(ms)


# ─── Duas ────────────────────────────────────────────────────────────────────

@router.get("/{child_id}/duas", response_model=list[DuaTeachingResponse])
async def list_dua_progress(child_id: UUID, current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    logs = await repo.get_for_child(child_id)
    return [DuaTeachingResponse.model_validate(l) for l in logs]


@router.post("/{child_id}/duas", response_model=DuaTeachingResponse, status_code=201)
async def log_dua(child_id: UUID, payload: DuaTeachingCreate, current_user: CurrentUser,
                   db: DB, repo: DuaTeachingRepo):
    log = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())
    return DuaTeachingResponse.model_validate(log)


@router.patch("/{child_id}/duas/{log_id}", response_model=DuaTeachingResponse)
async def update_dua(child_id: UUID, log_id: UUID, payload: DuaTeachingUpdate,
                      current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    log = await repo.get_owned_or_404(log_id, current_user.id)
    log = await repo.update(log, **payload.model_dump(exclude_none=True))
    return DuaTeachingResponse.model_validate(log)


@router.post("/{child_id}/duas/from-library", response_model=DuaTeachingResponse, status_code=201)
async def add_dua_from_library(child_id: UUID, key: str, current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    from app.services.child_duas import get_dua_by_key
    dua = get_dua_by_key(key)
    if not dua:
        raise HTTPException(404, "Dua not found in library")
    
    # check if already added
    existing = await repo.get_for_child(child_id)
    for e in existing:
        if e.dua_key == key:
            return DuaTeachingResponse.model_validate(e)
            
    log = await repo.create(
        child_id=child_id, user_id=current_user.id,
        dua_key=key, dua_name=dua["name"],
        started_date=date.today(),
        status="not_started"
    )
    return DuaTeachingResponse.model_validate(log)


@router.post("/{child_id}/duas/{log_id}/practice", response_model=ChildActivityResult)
async def practice_dua(child_id: UUID, log_id: UUID, current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    from app.models.child import ChildActivityLog
    from app.services.child_gamification import process_activity
    from app.routers.child import ChildRepo
    
    child_repo = ChildRepo(db)
    child = await child_repo.get_owned_or_404(child_id, current_user.id)
    
    log = await repo.get_owned_or_404(log_id, current_user.id)
    
    # update dua log
    log.practice_count += 1
    log.last_practiced = date.today()
    if log.status == "not_started":
        log.status = "learning"
    
    # create activity log for gamification
    activity = ChildActivityLog(
        child_id=child.id,
        user_id=current_user.id,
        activity_key=f"practice_dua_{log.dua_key}",
        activity_name=f"Practiced Dua: {log.dua_name}",
        activity_category="dua",
        xp_earned=5,  # 5 xp per practice
        completed=True,
        log_date=date.today(),
        logged_by="parent"
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)
    
    result = await process_activity(db, child, current_user.id, activity)
    
    return ChildActivityResult(
        activity=ChildActivityLogResponse.model_validate(activity),
        **result,
        new_badges=[ChildBadgeResponse.model_validate(b) for b in result["new_badges"]],
    )


# ─── Lessons & Curriculum ───────────────────────────────────────────────────

@router.get("/curriculum")
async def get_curriculum_endpoint(age_group: str = Query(default="young")):
    from app.services.child_curriculum import get_curriculum
    return get_curriculum(age_group)

@router.get("/{child_id}/lessons", response_model=list[LessonLogResponse])
async def list_lessons(child_id: UUID, current_user: CurrentUser, db: DB, repo: LessonLogRepo,
                        subject: str = Query(default=None)):
    logs = await repo.get_for_child(child_id, subject=subject)
    return [LessonLogResponse.model_validate(l) for l in logs]


@router.get("/{child_id}/lessons/stats")
async def lesson_stats(child_id: UUID, current_user: CurrentUser, db: DB, repo: LessonLogRepo):
    logs = await repo.get_for_child(child_id)
    stats = {}
    total_minutes = 0
    for log in logs:
        if log.subject not in stats:
            stats[log.subject] = {"count": 0, "minutes": 0}
        stats[log.subject]["count"] += 1
        minutes = log.duration_minutes or 0
        stats[log.subject]["minutes"] += minutes
        total_minutes += minutes
    
    return {
        "total_lessons": len(logs),
        "total_minutes": total_minutes,
        "by_subject": stats
    }


@router.post("/{child_id}/lessons", response_model=ChildActivityResult, status_code=201)
async def log_lesson(child_id: UUID, payload: LessonLogCreate, current_user: CurrentUser,
                      db: DB, repo: LessonLogRepo):
    from app.models.child import ChildActivityLog
    from app.services.child_gamification import process_activity
    from app.routers.child import ChildRepo

    child_repo = ChildRepo(db)
    child = await child_repo.get_owned_or_404(child_id, current_user.id)

    log = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())

    # Create gamification activity log
    activity = ChildActivityLog(
        child_id=child.id,
        user_id=current_user.id,
        activity_key=f"lesson_{log.subject.lower()}",
        activity_name=f"Learned {log.subject}: {log.topic}",
        activity_category="lesson",
        xp_earned=15, # Base XP for a lesson
        completed=True,
        log_date=payload.lesson_date or date.today(),
        logged_by="parent",
        duration_minutes=payload.duration_minutes
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)

    result = await process_activity(db, child, current_user.id, activity)

    return ChildActivityResult(
        activity=ChildActivityLogResponse.model_validate(activity),
        **result,
        new_badges=[ChildBadgeResponse.model_validate(b) for b in result["new_badges"]],
    )


# ─── Activities (XP / Gamification) ─────────────────────────────────────────

@router.get("/{child_id}/activities", response_model=list[ChildActivityLogResponse])
async def list_activities(
    child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo,
    limit: int = Query(default=30, le=100),
    category: Optional[str] = Query(default=None),
):
    from app.models.child import ChildActivityLog
    stmt = (
        select(ChildActivityLog)
        .where(ChildActivityLog.child_id == child_id)
        .order_by(ChildActivityLog.log_date.desc(), ChildActivityLog.created_at.desc())
        .limit(limit)
    )
    if category:
        stmt = stmt.where(ChildActivityLog.activity_category == category)
    result = await db.execute(stmt)
    return [ChildActivityLogResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/{child_id}/activities", response_model=ChildActivityResult, status_code=201)
async def log_activity(
    child_id: UUID, payload: ChildActivityLogCreate,
    current_user: CurrentUser, db: DB, repo: ChildRepo,
):
    from app.models.child import ChildActivityLog
    from app.services.child_gamification import process_activity

    child = await repo.get_owned_or_404(child_id, current_user.id)

    log_date = payload.log_date or date.today()
    activity = ChildActivityLog(
        child_id=child.id,
        user_id=current_user.id,
        activity_key=payload.activity_key,
        activity_name=payload.activity_name,
        activity_category=payload.activity_category,
        xp_earned=payload.xp_earned,
        duration_minutes=payload.duration_minutes,
        completed=payload.completed,
        log_date=log_date,
        notes=payload.notes,
        logged_by=payload.logged_by,
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)

    result = await process_activity(db, child, current_user.id, activity)

    return ChildActivityResult(
        activity=ChildActivityLogResponse.model_validate(activity),
        **result,
        new_badges=[ChildBadgeResponse.model_validate(b) for b in result["new_badges"]],
    )


# ─── Badges ──────────────────────────────────────────────────────────────────

@router.get("/{child_id}/badges", response_model=list[ChildBadgeResponse])
async def list_badges(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildBadge
    await repo.get_owned_or_404(child_id, current_user.id)
    result = await db.execute(
        select(ChildBadge)
        .where(ChildBadge.child_id == child_id)
        .order_by(ChildBadge.earned_date.desc())
    )
    return [ChildBadgeResponse.model_validate(b) for b in result.scalars().all()]


@router.get("/badges/all-definitions")
async def badge_definitions():
    from app.services.child_gamification import BADGE_DEFINITIONS
    return BADGE_DEFINITIONS


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/{child_id}/stats")
async def child_stats(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildActivityLog, ChildBadge, xp_to_level, LEVEL_THRESHOLDS

    child = await repo.get_owned_or_404(child_id, current_user.id)

    # Activity counts by category
    cat_result = await db.execute(
        select(ChildActivityLog.activity_category, func.count().label("cnt"))
        .where(ChildActivityLog.child_id == child_id, ChildActivityLog.completed == True)
        .group_by(ChildActivityLog.activity_category)
    )
    category_breakdown = {row.activity_category: row.cnt for row in cat_result.all()}

    # Total activities
    total_result = await db.execute(
        select(func.count()).select_from(ChildActivityLog)
        .where(ChildActivityLog.child_id == child_id, ChildActivityLog.completed == True)
    )
    total_activities = total_result.scalar_one()

    # Badge count
    badge_result = await db.execute(
        select(func.count()).select_from(ChildBadge).where(ChildBadge.child_id == child_id)
    )
    badge_count = badge_result.scalar_one()

    # Next level XP
    _, level_name = xp_to_level(child.xp_total)
    next_level_xp = next(
        (t for lvl, t, _ in LEVEL_THRESHOLDS if lvl == child.level + 1), None
    )

    return {
        "child_id": child_id,
        "name": child.name,
        "age_group": child.age_group,
        "xp_total": child.xp_total,
        "level": child.level,
        "level_name": level_name,
        "next_level_xp": next_level_xp,
        "current_streak": child.current_streak,
        "longest_streak": child.longest_streak,
        "total_activities": total_activities,
        "badge_count": badge_count,
        "category_breakdown": category_breakdown,
    }

@router.get("/{child_id}/analytics")
async def child_analytics(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildActivityLog, ChildBadge, ChildMilestone, ChildQuranProgress, DuaTeachingLog, ChildStoryProgress
    from datetime import timedelta

    child = await repo.get_owned_or_404(child_id, current_user.id)
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # 1. 30-day activity heatmap
    heatmap_result = await db.execute(
        select(ChildActivityLog.log_date, func.count().label("cnt"))
        .where(ChildActivityLog.child_id == child_id, ChildActivityLog.log_date >= thirty_days_ago)
        .group_by(ChildActivityLog.log_date)
    )
    heatmap = {row.log_date.isoformat(): row.cnt for row in heatmap_result.all()}

    # 2. Milestones progress
    ms_result = await db.execute(select(ChildMilestone.category, ChildMilestone.is_completed).where(ChildMilestone.child_id == child_id))
    milestones = ms_result.all()
    ms_stats = {"achieved": 0, "total": len(milestones), "by_category": {}}
    for cat, completed in milestones:
        if cat not in ms_stats["by_category"]: ms_stats["by_category"][cat] = {"achieved": 0, "total": 0}
        ms_stats["by_category"][cat]["total"] += 1
        if completed: 
            ms_stats["by_category"][cat]["achieved"] += 1
            ms_stats["achieved"] += 1

    # 3. Quran progress
    quran_result = await db.execute(select(ChildQuranProgress.status, ChildQuranProgress.ayahs_memorized).where(ChildQuranProgress.child_id == child_id))
    quran_logs = quran_result.all()
    quran_stats = {
        "surahs_memorized": sum(1 for q in quran_logs if q.status == "memorized"),
        "surahs_learning": sum(1 for q in quran_logs if q.status in ["learning", "memorizing"]),
        "total_ayahs": sum(q.ayahs_memorized for q in quran_logs)
    }

    # 4. Duas progress
    dua_result = await db.execute(select(DuaTeachingLog.status).where(DuaTeachingLog.child_id == child_id))
    dua_logs = dua_result.all()
    dua_stats = {
        "mastered": sum(1 for d in dua_logs if d.status == "mastered"),
        "learning": sum(1 for d in dua_logs if d.status in ["learning", "practicing"]),
        "total": len(dua_logs)
    }

    # 5. Stories read
    story_result = await db.execute(select(func.count()).select_from(ChildStoryProgress).where(ChildStoryProgress.child_id == child_id, ChildStoryProgress.times_read > 0))
    stories_read = story_result.scalar_one()

    return {
        "child_id": child_id,
        "heatmap": heatmap,
        "milestones_progress": ms_stats,
        "quran_progress": quran_stats,
        "duas_progress": dua_stats,
        "stories_read": stories_read,
    }


# ─── Stories ─────────────────────────────────────────────────────────────────

@router.get("/story-library")
async def get_story_library_endpoint(age_group: str = Query(default=None), category: str = Query(default=None)):
    from app.services.child_stories import get_stories_by_category
    return get_stories_by_category(age_group=age_group, category=category)

@router.get("/{child_id}/stories/progress", response_model=list[ChildStoryProgressResponse])
async def list_story_progress(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildStoryProgress
    await repo.get_owned_or_404(child_id, current_user.id)
    result = await db.execute(
        select(ChildStoryProgress).where(ChildStoryProgress.child_id == child_id)
    )
    return [ChildStoryProgressResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/{child_id}/stories/{key}/complete", response_model=ChildStoryProgressResponse)
async def complete_story(child_id: UUID, key: str, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildStoryProgress
    from app.services.child_stories import get_story_by_key
    
    child = await repo.get_owned_or_404(child_id, current_user.id)
    story_def = get_story_by_key(key)
    if not story_def:
        raise HTTPException(404, "Story not found")
        
    result = await db.execute(
        select(ChildStoryProgress).where(
            ChildStoryProgress.child_id == child_id,
            ChildStoryProgress.story_key == key
        )
    )
    progress = result.scalar_one_or_none()
    
    if progress:
        progress.times_read += 1
        progress.completed_date = date.today()
    else:
        progress = ChildStoryProgress(
            child_id=child_id,
            user_id=current_user.id,
            story_key=key,
            started_date=date.today(),
            completed_date=date.today(),
            times_read=1,
            xp_earned=15, # base XP for story
        )
        db.add(progress)
        
    await db.flush()
    await db.refresh(progress)
    return ChildStoryProgressResponse.model_validate(progress)


@router.post("/{child_id}/stories/{key}/favorite", response_model=ChildStoryProgressResponse)
async def toggle_favorite_story(child_id: UUID, key: str, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildStoryProgress
    
    await repo.get_owned_or_404(child_id, current_user.id)
    result = await db.execute(
        select(ChildStoryProgress).where(
            ChildStoryProgress.child_id == child_id,
            ChildStoryProgress.story_key == key
        )
    )
    progress = result.scalar_one_or_none()
    
    if progress:
        progress.is_favorite = not progress.is_favorite
    else:
        progress = ChildStoryProgress(
            child_id=child_id,
            user_id=current_user.id,
            story_key=key,
            is_favorite=True,
        )
        db.add(progress)
        
    await db.flush()
    await db.refresh(progress)
    return ChildStoryProgressResponse.model_validate(progress)


# ─── Quran Memorization ──────────────────────────────────────────────────────

@router.get("/{child_id}/quran", response_model=list[ChildQuranProgressResponse])
async def list_quran_progress(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildQuranProgress
    await repo.get_owned_or_404(child_id, current_user.id)
    result = await db.execute(
        select(ChildQuranProgress)
        .where(ChildQuranProgress.child_id == child_id)
        .order_by(ChildQuranProgress.surah_number.asc())
    )
    return [ChildQuranProgressResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/{child_id}/quran", response_model=ChildQuranProgressResponse, status_code=201)
async def track_surah(child_id: UUID, payload: dict, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildQuranProgress
    await repo.get_owned_or_404(child_id, current_user.id)
    
    surah_number = payload.get("surah_number")
    surah_name = payload.get("surah_name")
    total_ayahs = payload.get("total_ayahs")
    
    if not surah_number or not surah_name or not total_ayahs:
        raise HTTPException(400, "Missing required surah fields")
        
    result = await db.execute(
        select(ChildQuranProgress).where(
            ChildQuranProgress.child_id == child_id,
            ChildQuranProgress.surah_number == surah_number
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Surah already being tracked")
        
    progress = ChildQuranProgress(
        child_id=child_id,
        user_id=current_user.id,
        surah_number=surah_number,
        surah_name=surah_name,
        total_ayahs=total_ayahs,
        status="learning",
        started_date=date.today(),
    )
    db.add(progress)
    await db.flush()
    await db.refresh(progress)
    return ChildQuranProgressResponse.model_validate(progress)


@router.patch("/{child_id}/quran/{surah_number}", response_model=ChildQuranProgressResponse)
async def update_surah_progress(child_id: UUID, surah_number: int, payload: ChildQuranProgressUpdate, current_user: CurrentUser, db: DB, repo: ChildRepo):
    from app.models.child import ChildQuranProgress
    await repo.get_owned_or_404(child_id, current_user.id)
    
    result = await db.execute(
        select(ChildQuranProgress).where(
            ChildQuranProgress.child_id == child_id,
            ChildQuranProgress.surah_number == surah_number
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(404, "Surah not being tracked")
        
    if payload.status is not None:
        progress.status = payload.status
        if payload.status == "memorized" and not progress.memorized_date:
            progress.memorized_date = date.today()
    
    if payload.ayahs_memorized is not None:
        progress.ayahs_memorized = payload.ayahs_memorized
        
    if payload.quality_rating is not None:
        progress.quality_rating = payload.quality_rating
        progress.last_reviewed = date.today()
        
    if payload.notes is not None:
        progress.notes = payload.notes
        
    await db.flush()
    await db.refresh(progress)
    return ChildQuranProgressResponse.model_validate(progress)
