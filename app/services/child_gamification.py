"""
Child Gamification Service
==========================
Handles XP awards, level-up logic, streak calculation, and badge awards.
Called from the child router whenever an activity is logged.
"""
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child, ChildActivityLog, ChildBadge, xp_to_level

# ─── Badge Definitions ────────────────────────────────────────────────────────

BADGE_DEFINITIONS = [
    # First-time badges
    {"key": "first_activity",     "name": "First Step",         "icon": "footprints",   "category": "achievement", "xp": 10},
    {"key": "first_quran",        "name": "Quran Explorer",     "icon": "book-open",    "category": "achievement", "xp": 20},
    {"key": "first_dua",          "name": "Dua Beginner",       "icon": "hand-heart",   "category": "achievement", "xp": 15},
    {"key": "first_salah",        "name": "Salah Starter",      "icon": "moon-star",    "category": "achievement", "xp": 20},
    {"key": "first_story",        "name": "Story Lover",        "icon": "library",      "category": "achievement", "xp": 15},
    # Streak badges
    {"key": "streak_3",           "name": "3-Day Streak",       "icon": "flame",        "category": "streak", "xp": 25},
    {"key": "streak_7",           "name": "Week Warrior",       "icon": "flame",        "category": "streak", "xp": 50},
    {"key": "streak_30",          "name": "Month Champion",     "icon": "flame",        "category": "streak", "xp": 150},
    # Activity count badges
    {"key": "quran_5",            "name": "Quran Buddy",        "icon": "book-open",    "category": "milestone", "xp": 30},
    {"key": "quran_20",           "name": "Quran Hero",         "icon": "book-open",    "category": "milestone", "xp": 75},
    {"key": "dua_5_mastered",     "name": "Dua Master",         "icon": "hand-heart",   "category": "milestone", "xp": 40},
    {"key": "salah_10",           "name": "Salah Champion",     "icon": "mosque",       "category": "milestone", "xp": 60},
    {"key": "story_10",           "name": "Story Seeker",       "icon": "library",      "category": "milestone", "xp": 35},
    {"key": "story_25",           "name": "Seerah Scholar",     "icon": "library",      "category": "milestone", "xp": 80},
    {"key": "akhlaq_10",          "name": "Good Character",     "icon": "heart",        "category": "milestone", "xp": 50},
    # Level badges (auto-awarded on level-up)
    {"key": "level_3",            "name": "Rising Star",        "icon": "star",         "category": "level", "xp": 0},
    {"key": "level_5",            "name": "Halfway Hero",       "icon": "trophy",       "category": "level", "xp": 0},
    {"key": "level_10",           "name": "Young Scholar",      "icon": "graduation-cap", "category": "level", "xp": 0},
    # Special
    {"key": "all_categories",     "name": "Well Rounded",       "icon": "sparkles",     "category": "achievement", "xp": 60},
]

BADGE_MAP = {b["key"]: b for b in BADGE_DEFINITIONS}


# ─── Core Logic ──────────────────────────────────────────────────────────────

async def _has_badge(db: AsyncSession, child_id: UUID, badge_key: str) -> bool:
    r = await db.execute(
        select(ChildBadge).where(
            ChildBadge.child_id == child_id,
            ChildBadge.badge_key == badge_key,
        )
    )
    return r.scalar_one_or_none() is not None


async def _award_badge(
    db: AsyncSession, child: Child, user_id: UUID, badge_key: str
) -> ChildBadge | None:
    """Award a badge if not already earned. Returns the new badge or None."""
    if await _has_badge(db, child.id, badge_key):
        return None
    defn = BADGE_MAP.get(badge_key)
    if not defn:
        return None
    badge = ChildBadge(
        child_id=child.id,
        user_id=user_id,
        badge_key=badge_key,
        badge_name=defn["name"],
        badge_icon=defn["icon"],
        badge_category=defn["category"],
        earned_date=date.today(),
        xp_awarded=defn["xp"],
    )
    db.add(badge)
    await db.flush()
    await db.refresh(badge)
    return badge


async def process_activity(
    db: AsyncSession,
    child: Child,
    user_id: UUID,
    activity_log: ChildActivityLog,
) -> dict:
    """
    After an activity is saved, recalculate XP, streak, level, and check badges.
    Returns a dict with xp_gained, new_total_xp, new_level, level_name, leveled_up, new_badges[].
    """
    today = date.today()
    xp_gained = activity_log.xp_earned
    old_level = child.level

    # ── Update XP ──────────────────────────────────────────────────────────
    child.xp_total = (child.xp_total or 0) + xp_gained
    new_level, level_name = xp_to_level(child.xp_total)
    child.level = new_level
    leveled_up = new_level > old_level

    # ── Update streak ───────────────────────────────────────────────────────
    last = child.last_activity_date
    if last is None or last < today:
        if last == today - timedelta(days=1):
            child.current_streak = (child.current_streak or 0) + 1
        elif last == today:
            pass  # already counted today
        else:
            child.current_streak = 1
        child.longest_streak = max(child.longest_streak or 0, child.current_streak)
        child.last_activity_date = today

    await db.flush()

    # ── Check and award badges ──────────────────────────────────────────────
    new_badges: list[ChildBadge] = []

    async def _try_award(key: str):
        b = await _award_badge(db, child, user_id, key)
        if b:
            new_badges.append(b)

    # Count totals by category
    r_total = await db.execute(
        select(func.count()).select_from(ChildActivityLog).where(
            ChildActivityLog.child_id == child.id,
            ChildActivityLog.completed == True,
        )
    )
    total_activities = r_total.scalar_one()

    async def _count_cat(cat: str) -> int:
        r = await db.execute(
            select(func.count()).select_from(ChildActivityLog).where(
                ChildActivityLog.child_id == child.id,
                ChildActivityLog.activity_category == cat,
                ChildActivityLog.completed == True,
            )
        )
        return r.scalar_one()

    cat = activity_log.activity_category

    # First-ever activity
    if total_activities == 1:
        await _try_award("first_activity")

    # First in each category
    if cat == "quran":
        quran_count = await _count_cat("quran")
        if quran_count == 1:
            await _try_award("first_quran")
        if quran_count >= 5:
            await _try_award("quran_5")
        if quran_count >= 20:
            await _try_award("quran_20")
    elif cat == "salah":
        salah_count = await _count_cat("salah")
        if salah_count == 1:
            await _try_award("first_salah")
        if salah_count >= 10:
            await _try_award("salah_10")
    elif cat == "dua":
        dua_count = await _count_cat("dua")
        if dua_count == 1:
            await _try_award("first_dua")
    elif cat == "story":
        story_count = await _count_cat("story")
        if story_count == 1:
            await _try_award("first_story")
        if story_count >= 10:
            await _try_award("story_10")
        if story_count >= 25:
            await _try_award("story_25")
    elif cat == "akhlaq":
        akhlaq_count = await _count_cat("akhlaq")
        if akhlaq_count >= 10:
            await _try_award("akhlaq_10")

    # Streak badges
    streak = child.current_streak or 0
    if streak >= 3:
        await _try_award("streak_3")
    if streak >= 7:
        await _try_award("streak_7")
    if streak >= 30:
        await _try_award("streak_30")

    # Level badges
    if leveled_up:
        if new_level >= 3:
            await _try_award("level_3")
        if new_level >= 5:
            await _try_award("level_5")
        if new_level >= 10:
            await _try_award("level_10")

    # All-categories badge
    cats_used_r = await db.execute(
        select(ChildActivityLog.activity_category).distinct().where(
            ChildActivityLog.child_id == child.id,
            ChildActivityLog.completed == True,
        )
    )
    cats_used = {row[0] for row in cats_used_r.all()}
    required_cats = {"quran", "salah", "dua", "story", "akhlaq"}
    if required_cats.issubset(cats_used):
        await _try_award("all_categories")

    # Award bonus XP for badges
    bonus_xp = sum(b.xp_awarded for b in new_badges)
    if bonus_xp:
        child.xp_total += bonus_xp
        new_level, level_name = xp_to_level(child.xp_total)
        child.level = new_level
        leveled_up = leveled_up or (new_level > old_level)

    await db.flush()

    return {
        "xp_gained": xp_gained,
        "new_total_xp": child.xp_total,
        "new_level": child.level,
        "level_name": level_name,
        "leveled_up": leveled_up,
        "new_badges": new_badges,
    }
