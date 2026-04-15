"""
Gamification Router — Phase 7
==============================
GET  /gamification/profile        — total XP, level, rank
GET  /gamification/xp/history     — recent XP events
POST /gamification/xp/award       — award XP (internal/admin)
GET  /gamification/badges         — all badge definitions
GET  /gamification/badges/mine    — user's earned badges
GET  /gamification/quests         — available quests
GET  /gamification/quests/active  — user's active quests
POST /gamification/quests/{id}/start   — start a quest
POST /gamification/quests/{id}/update  — update progress
POST /gamification/badges/seed    — seed badge catalogue
POST /gamification/quests/seed    — seed quest catalogue
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, desc

from app.core.dependencies import CurrentUser, DB
from app.models.gamification import UserXP, Badge, UserBadge, Quest, UserQuest, XPSource, QuestStatus

router = APIRouter(prefix="/gamification", tags=["gamification"])

# ─── XP / Level helpers ───────────────────────────────────────────────────────

XP_PER_ACTION = {
    XPSource.PRAYER_LOGGED:  10,
    XPSource.PRAYER_STREAK:  25,
    XPSource.QURAN_READ:      8,
    XPSource.HIFZ_REVIEW:    15,
    XPSource.HABIT_COMPLETE:   5,
    XPSource.HABIT_STREAK:    20,
    XPSource.JOURNAL_ENTRY:   12,
    XPSource.DHIKR_SESSION:    8,
    XPSource.FASTING:         30,
    XPSource.QUEST_COMPLETE: 100,
    XPSource.BADGE_EARNED:    50,
    XPSource.DAILY_LOGIN:      5,
}

LEVELS = [
    (0,      "Seeker",      "🌱"),
    (100,    "Devotee",     "📿"),
    (300,    "Observer",    "👁️"),
    (600,    "Worshipper",  "🕌"),
    (1000,   "Believer",    "⭐"),
    (1500,   "Sincere",     "✨"),
    (2200,   "Righteous",   "🌿"),
    (3000,   "Pious",       "📖"),
    (4000,   "Scholar",     "🎓"),
    (5500,   "Devoted",     "💎"),
    (7500,   "Imam",        "🏆"),
    (10000,  "Wali",        "🌟"),
]

def get_level(total_xp: int) -> dict:
    level = 0
    title = LEVELS[0][1]
    icon  = LEVELS[0][2]
    for i, (threshold, t, ic) in enumerate(LEVELS):
        if total_xp >= threshold:
            level = i + 1
            title = t
            icon  = ic
    # XP to next level
    next_idx = min(level, len(LEVELS) - 1)
    next_threshold = LEVELS[next_idx][0] if next_idx < len(LEVELS) else LEVELS[-1][0]
    prev_threshold = LEVELS[level - 1][0] if level > 0 else 0
    range_xp = next_threshold - prev_threshold
    in_range  = total_xp - prev_threshold
    pct = round((in_range / range_xp) * 100) if range_xp > 0 else 100
    return {
        "level": level,
        "title": title,
        "icon": icon,
        "total_xp": total_xp,
        "xp_to_next": max(0, next_threshold - total_xp),
        "level_progress_pct": pct,
    }

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_gamification_profile(current_user: CurrentUser, db: DB):
    """Full gamification profile: level, XP, recent badges, quests."""
    # Total XP
    total_xp_result = await db.execute(select(func.sum(UserXP.amount)).where(UserXP.user_id == current_user.id))
    total_xp = total_xp_result.scalar() or 0
    profile = get_level(total_xp)

    # Badges
    badges_result = await db.execute(
        select(UserBadge, Badge).join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == current_user.id)
        .order_by(desc(UserBadge.earned_at))
    )
    badges = [{"badge": {"slug": b.slug, "name": b.name, "icon": b.icon, "category": b.category, "rarity": b.rarity}, "earned_at": ub.earned_at.isoformat()} for ub, b in badges_result.all()]

    # Active quests
    quests_result = await db.execute(
        select(UserQuest, Quest).join(Quest, UserQuest.quest_id == Quest.id)
        .where(UserQuest.user_id == current_user.id, UserQuest.status == QuestStatus.ACTIVE)
    )
    quests = [{"id": str(uq.id), "title": q.title, "icon": q.icon, "progress": uq.progress, "target": uq.target, "pct": round((uq.progress / uq.target) * 100) if uq.target else 0, "xp_reward": q.xp_reward} for uq, q in quests_result.all()]

    return {**profile, "badges": badges, "active_quests": quests, "badge_count": len(badges)}


@router.get("/xp/history")
async def get_xp_history(current_user: CurrentUser, db: DB, limit: int = Query(default=50, le=200)):
    result = await db.execute(select(UserXP).where(UserXP.user_id == current_user.id).order_by(desc(UserXP.earned_at)).limit(limit))
    events = result.scalars().all()
    return [{"id": str(e.id), "source": e.source, "amount": e.amount, "note": e.note, "earned_at": e.earned_at.isoformat()} for e in events]


@router.post("/xp/award")
async def award_xp(current_user: CurrentUser, db: DB, source: str, amount: Optional[int] = None, note: Optional[str] = None):
    """Award XP to the current user. Amount defaults to the configured value for the source."""
    try:
        xp_src = XPSource(source)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid XP source: {source}")
    amt = amount or XP_PER_ACTION.get(xp_src, 5)
    event = UserXP(user_id=current_user.id, source=xp_src, amount=amt, note=note, earned_at=datetime.utcnow())
    db.add(event)
    await db.commit()
    total_xp_result = await db.execute(select(func.sum(UserXP.amount)).where(UserXP.user_id == current_user.id))
    total_xp = total_xp_result.scalar() or 0
    return {"awarded": amt, "total_xp": total_xp, **get_level(total_xp)}


@router.get("/badges")
async def list_badges(db: DB):
    result = await db.execute(select(Badge).order_by(Badge.category, Badge.name))
    badges = result.scalars().all()
    return [{"slug": b.slug, "name": b.name, "description": b.description, "icon": b.icon, "category": b.category, "xp_reward": b.xp_reward, "rarity": b.rarity} for b in badges]


@router.get("/badges/mine")
async def my_badges(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(UserBadge, Badge).join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == current_user.id)
        .order_by(desc(UserBadge.earned_at))
    )
    return [{"slug": b.slug, "name": b.name, "icon": b.icon, "category": b.category, "rarity": b.rarity, "earned_at": ub.earned_at.isoformat()} for ub, b in result.all()]


@router.get("/quests")
async def list_quests(db: DB):
    result = await db.execute(select(Quest).where(Quest.is_active == True).order_by(Quest.quest_type, Quest.title))
    quests = result.scalars().all()
    return [{"id": str(q.id), "slug": q.slug, "title": q.title, "description": q.description, "icon": q.icon, "quest_type": q.quest_type, "xp_reward": q.xp_reward, "duration_days": q.duration_days} for q in quests]


@router.get("/quests/active")
async def active_quests(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(UserQuest, Quest).join(Quest, UserQuest.quest_id == Quest.id)
        .where(UserQuest.user_id == current_user.id, UserQuest.status == QuestStatus.ACTIVE)
    )
    return [{"id": str(uq.id), "quest_id": str(uq.quest_id), "title": q.title, "icon": q.icon, "description": q.description, "quest_type": q.quest_type, "xp_reward": q.xp_reward, "progress": uq.progress, "target": uq.target, "pct": round((uq.progress / uq.target) * 100) if uq.target else 0, "started_at": uq.started_at.isoformat(), "expires_at": uq.expires_at.isoformat() if uq.expires_at else None} for uq, q in result.all()]


@router.post("/quests/{quest_id}/start")
async def start_quest(quest_id: UUID, current_user: CurrentUser, db: DB):
    quest = await db.get(Quest, quest_id)
    if not quest:
        raise HTTPException(404, "Quest not found")
    # Check not already active
    existing = await db.execute(select(UserQuest).where(UserQuest.user_id == current_user.id, UserQuest.quest_id == quest_id, UserQuest.status == QuestStatus.ACTIVE))
    if existing.scalar():
        raise HTTPException(409, "Quest already active")
    expires = datetime.utcnow() + timedelta(days=quest.duration_days) if quest.duration_days else None
    uq = UserQuest(user_id=current_user.id, quest_id=quest_id, status=QuestStatus.ACTIVE, progress=0, target=quest.criteria.get("target", 1) if quest.criteria else 1, started_at=datetime.utcnow(), expires_at=expires)
    db.add(uq)
    await db.commit()
    await db.refresh(uq)
    return {"id": str(uq.id), "quest_id": str(quest_id), "status": uq.status, "target": uq.target}


@router.post("/quests/{user_quest_id}/update")
async def update_quest_progress(user_quest_id: UUID, current_user: CurrentUser, db: DB, progress: int = Query(...)):
    uq = await db.get(UserQuest, user_quest_id)
    if not uq or uq.user_id != current_user.id:
        raise HTTPException(404, "Quest not found")
    uq.progress = min(progress, uq.target)
    if uq.progress >= uq.target:
        uq.status = QuestStatus.COMPLETED
        uq.completed_at = datetime.utcnow()
        quest = await db.get(Quest, uq.quest_id)
        # Award XP
        xp_event = UserXP(user_id=current_user.id, source=XPSource.QUEST_COMPLETE, amount=quest.xp_reward if quest else 100, note=f"Quest: {quest.title if quest else 'Unknown'}", earned_at=datetime.utcnow())
        db.add(xp_event)
    await db.commit()
    return {"status": uq.status, "progress": uq.progress, "target": uq.target}


# ─── Seed routes ──────────────────────────────────────────────────────────────

BADGE_CATALOGUE = [
    {"slug": "first_prayer", "name": "First Prayer", "description": "Log your very first prayer in Deen", "icon": "🌅", "category": "prayer", "xp_reward": 50, "rarity": "common"},
    {"slug": "prayer_7_streak", "name": "Week Warrior", "description": "7-day prayer streak — all 5 prayers!", "icon": "🔥", "category": "prayer", "xp_reward": 150, "rarity": "rare"},
    {"slug": "prayer_30_streak", "name": "Steadfast", "description": "30-day perfect prayer streak", "icon": "💎", "category": "prayer", "xp_reward": 500, "rarity": "epic"},
    {"slug": "prayer_jama", "name": "Congregation Leader", "description": "Prayed 10 prayers in congregation", "icon": "🕌", "category": "prayer", "xp_reward": 100, "rarity": "common"},
    {"slug": "quran_first_surah", "name": "Reciter", "description": "Read your first surah", "icon": "📖", "category": "quran", "xp_reward": 50, "rarity": "common"},
    {"slug": "quran_10_surahs", "name": "Scholar's Path", "description": "Read 10 different surahs", "icon": "📚", "category": "quran", "xp_reward": 200, "rarity": "rare"},
    {"slug": "hifz_first", "name": "Memoriser", "description": "Begin your hifz journey", "icon": "🧠", "category": "quran", "xp_reward": 100, "rarity": "common"},
    {"slug": "habit_first", "name": "New Habit", "description": "Create your first Islamic habit", "icon": "✅", "category": "habits", "xp_reward": 50, "rarity": "common"},
    {"slug": "habit_7_streak", "name": "Consistent", "description": "7-day habit streak", "icon": "⚡", "category": "habits", "xp_reward": 150, "rarity": "rare"},
    {"slug": "journal_first", "name": "Reflector", "description": "Write your first journal entry", "icon": "✍️", "category": "journal", "xp_reward": 50, "rarity": "common"},
    {"slug": "journal_30", "name": "Muhasabah Master", "description": "30 journal entries", "icon": "📓", "category": "journal", "xp_reward": 300, "rarity": "epic"},
    {"slug": "ramadan_complete", "name": "Ramadan Champion", "description": "Log all fasts in Ramadan", "icon": "🌙", "category": "fasting", "xp_reward": 1000, "rarity": "legendary"},
    {"slug": "level_10", "name": "Devoted", "description": "Reach level 10", "icon": "🏆", "category": "special", "xp_reward": 500, "rarity": "epic"},
]

QUEST_CATALOGUE = [
    {"slug": "daily_5_prayers", "title": "Perfect Prayer Day", "description": "Log all 5 prayers today", "icon": "🌟", "quest_type": "daily", "xp_reward": 50, "duration_days": 1, "criteria": {"target": 5, "metric": "prayers_today"}},
    {"slug": "daily_quran", "title": "Daily Quran", "description": "Read at least 10 verses today", "icon": "📖", "quest_type": "daily", "xp_reward": 30, "duration_days": 1, "criteria": {"target": 10, "metric": "verses_today"}},
    {"slug": "daily_dhikr", "title": "Dhikr Session", "description": "Complete a dhikr session of 100 counts", "icon": "📿", "quest_type": "daily", "xp_reward": 25, "duration_days": 1, "criteria": {"target": 100, "metric": "dhikr_today"}},
    {"slug": "weekly_21_prayers", "title": "Prayer Champion", "description": "Log 21 prayers this week (3/day)", "icon": "🏆", "quest_type": "weekly", "xp_reward": 150, "duration_days": 7, "criteria": {"target": 21, "metric": "prayers_week"}},
    {"slug": "weekly_surah", "title": "Weekly Surah", "description": "Read 3 different surahs this week", "icon": "📚", "quest_type": "weekly", "xp_reward": 100, "duration_days": 7, "criteria": {"target": 3, "metric": "surahs_week"}},
    {"slug": "weekly_journal", "title": "Journal Journey", "description": "Write 5 journal entries this week", "icon": "📔", "quest_type": "weekly", "xp_reward": 120, "duration_days": 7, "criteria": {"target": 5, "metric": "journal_week"}},
    {"slug": "monthly_khatam", "title": "Khatam Quest", "description": "Read 200 verses this month", "icon": "🌿", "quest_type": "monthly", "xp_reward": 500, "duration_days": 30, "criteria": {"target": 200, "metric": "verses_month"}},
    {"slug": "fajr_warrior", "title": "Fajr Warrior", "description": "Log Fajr on time for 7 consecutive days", "icon": "🌅", "quest_type": "weekly", "xp_reward": 200, "duration_days": 7, "criteria": {"target": 7, "metric": "fajr_streak"}},
]


@router.post("/badges/seed")
async def seed_badges(db: DB, current_user: CurrentUser):
    from sqlalchemy import text
    for b in BADGE_CATALOGUE:
        existing = await db.execute(select(Badge).where(Badge.slug == b["slug"]))
        if not existing.scalar():
            db.add(Badge(**b))
    await db.commit()
    return {"message": f"Badge catalogue seeded ({len(BADGE_CATALOGUE)} badges)"}


@router.post("/quests/seed")
async def seed_quests(db: DB, current_user: CurrentUser):
    for q in QUEST_CATALOGUE:
        existing = await db.execute(select(Quest).where(Quest.slug == q["slug"]))
        if not existing.scalar():
            db.add(Quest(**q))
    await db.commit()
    return {"message": f"Quest catalogue seeded ({len(QUEST_CATALOGUE)} quests)"}
