"""
Child Upbringing Models
=======================
Child               — child profile
ChildMilestone      — developmental / Islamic milestone
DuaTeachingLog      — track which duas a child has learnt
IslamicLessonLog    — Quran, aqeedah, seerah lesson tracking
ChildBadge          — gamification badges earned by a child
ChildActivityLog    — daily activity records (for XP + streaks)
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.core.database import Base, TimestampMixin


def _calc_age_group(dob: date | None) -> str | None:
    """Derive age group string from date of birth."""
    if not dob:
        return None
    from datetime import date as _date
    months = (
        (_date.today().year - dob.year) * 12
        + (_date.today().month - dob.month)
    )
    if months < 48:   return "toddler"   # < 4 years
    if months < 84:   return "young"      # 4-6 years
    if months < 120:  return "middle"     # 7-9 years
    if months < 156:  return "preteen"    # 10-12 years
    return "teen"                          # 13+


LEVEL_THRESHOLDS = [
    (1, 0,    "Little Star"),
    (2, 50,   "Tiny Explorer"),
    (3, 150,  "Dua Learner"),
    (4, 300,  "Quran Buddy"),
    (5, 500,  "Salah Helper"),
    (6, 800,  "Seerah Seeker"),
    (7, 1200, "Akhlaq Champion"),
    (8, 1800, "Hafiz Helper"),
    (9, 2500, "Shining Star"),
    (10, 3500, "Young Scholar"),
]


def xp_to_level(xp: int) -> tuple[int, str]:
    """Return (level, level_name) for a given XP total."""
    level, name = 1, "Little Star"
    for lvl, threshold, lvl_name in LEVEL_THRESHOLDS:
        if xp >= threshold:
            level, name = lvl, lvl_name
    return level, name


class Child(Base, TimestampMixin):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))  # male, female, prefer_not_to_say
    avatar_emoji: Mapped[str] = mapped_column(String(10), default="🌟")
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Gamification ──────────────────────────────────────────────────────────
    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[date | None] = mapped_column(Date)
    age_group: Mapped[str | None] = mapped_column(String(20))  # toddler, young, middle, preteen, teen

    milestones: Mapped[list["ChildMilestone"]] = relationship(back_populates="child")
    dua_logs: Mapped[list["DuaTeachingLog"]] = relationship(back_populates="child")
    lesson_logs: Mapped[list["IslamicLessonLog"]] = relationship(back_populates="child")
    badges: Mapped[list["ChildBadge"]] = relationship(back_populates="child")
    activity_logs: Mapped[list["ChildActivityLog"]] = relationship(back_populates="child")


MILESTONE_CATEGORIES = [
    "aqeedah",     # belief foundations
    "salah",       # prayer
    "quran",       # Quran reading / memorisation
    "arabic",      # Arabic language
    "akhlaq",      # character / manners
    "seerah",      # prophetic history
    "fiqh",        # basic rulings (halal/haram for kids)
    "dua",         # supplications
    "physical",    # developmental
    "social",      # social development
]


class ChildMilestone(Base, TimestampMixin):
    __tablename__ = "child_milestones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    target_age_months: Mapped[int | None] = mapped_column(Integer)
    achieved: Mapped[bool] = mapped_column(Boolean, default=False)
    achieved_date: Mapped[date | None] = mapped_column(Date)
    celebration_note: Mapped[str | None] = mapped_column(Text)

    # Template milestones (system-defined, user can personalise)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)

    child: Mapped["Child"] = relationship(back_populates="milestones")


class DuaTeachingLog(Base, TimestampMixin):
    __tablename__ = "dua_teaching_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    dua_key: Mapped[str] = mapped_column(String(100), nullable=False)
    dua_name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_date: Mapped[date | None] = mapped_column(Date)
    mastered_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="not_started")  # not_started, learning, reciting, mastered
    practice_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)

    child: Mapped["Child"] = relationship(back_populates="dua_logs")


class IslamicLessonLog(Base, TimestampMixin):
    __tablename__ = "islamic_lesson_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    lesson_date: Mapped[date] = mapped_column(Date, nullable=False)
    subject: Mapped[str] = mapped_column(String(30), nullable=False)  # quran, arabic, aqeedah, seerah, fiqh
    topic: Mapped[str] = mapped_column(String(300), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)  # parent's rating 1-5

    child: Mapped["Child"] = relationship(back_populates="lesson_logs")


class ChildBadge(Base, TimestampMixin):
    """Badges earned by a child through the gamification system."""
    __tablename__ = "child_badges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    badge_key: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(200), nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(50), default="star")
    badge_category: Mapped[str] = mapped_column(String(50), default="achievement")  # achievement, milestone, streak
    earned_date: Mapped[date] = mapped_column(Date, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)

    child: Mapped["Child"] = relationship(back_populates="badges")


class ChildActivityLog(Base, TimestampMixin):
    """Records each activity a child completes — source of XP and streak calculation."""
    __tablename__ = "child_activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    activity_key: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_category: Mapped[str] = mapped_column(String(50), nullable=False)  # quran, salah, dua, story, akhlaq
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    logged_by: Mapped[str] = mapped_column(String(50), default="parent")

    child: Mapped["Child"] = relationship(back_populates="activity_logs")


class ChildStoryProgress(Base, TimestampMixin):
    __tablename__ = "child_story_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    story_key: Mapped[str] = mapped_column(String(100), nullable=False)
    started_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    times_read: Mapped[int] = mapped_column(Integer, default=0)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    child: Mapped["Child"] = relationship("Child", backref="story_progress")


class ChildQuranProgress(Base, TimestampMixin):
    __tablename__ = "child_quran_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    surah_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="not_started")  # not_started, learning, memorizing, reviewing, memorized
    ayahs_memorized: Mapped[int] = mapped_column(Integer, default=0)
    total_ayahs: Mapped[int] = mapped_column(Integer, nullable=False)
    
    started_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    memorized_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)
    quality_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    child: Mapped["Child"] = relationship("Child", backref="quran_progress")
