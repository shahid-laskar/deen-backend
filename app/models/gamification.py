"""
Gamification models — Phase 7
==============================
Tables: user_xp, user_badges, quests, user_quests, gamification_events
"""
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Float, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class BadgeCategory(str, PyEnum):
    PRAYER    = "prayer"
    QURAN     = "quran"
    HABITS    = "habits"
    JOURNAL   = "journal"
    FASTING   = "fasting"
    SOCIAL    = "social"
    SPECIAL   = "special"


class QuestStatus(str, PyEnum):
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"
    EXPIRED   = "expired"


class XPSource(str, PyEnum):
    PRAYER_LOGGED   = "prayer_logged"
    PRAYER_STREAK   = "prayer_streak"
    QURAN_READ      = "quran_read"
    HIFZ_REVIEW     = "hifz_review"
    HABIT_COMPLETE  = "habit_complete"
    HABIT_STREAK    = "habit_streak"
    JOURNAL_ENTRY   = "journal_entry"
    DHIKR_SESSION   = "dhikr_session"
    FASTING         = "fasting"
    QUEST_COMPLETE  = "quest_complete"
    BADGE_EARNED    = "badge_earned"
    DAILY_LOGIN     = "daily_login"


class UserXP(Base, TimestampMixin):
    """Cumulative XP ledger per user."""
    __tablename__ = "user_xp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(Enum(XPSource), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="xp_events")


class Badge(Base, TimestampMixin):
    """Badge definition catalogue."""
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="🏅")
    category: Mapped[str] = mapped_column(Enum(BadgeCategory), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    criteria: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"type":"prayer_streak","value":7}
    rarity: Mapped[str] = mapped_column(String(20), nullable=False, default="common")  # common|rare|epic|legendary


class UserBadge(Base, TimestampMixin):
    """Badges earned by a user."""
    __tablename__ = "user_badges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="badges")
    badge: Mapped["Badge"] = relationship("Badge")


class Quest(Base, TimestampMixin):
    """Quest template catalogue."""
    __tablename__ = "quests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="⚔️")
    quest_type: Mapped[str] = mapped_column(String(30), nullable=False)  # daily|weekly|monthly|special
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    badge_slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # award badge on complete
    criteria: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserQuest(Base, TimestampMixin):
    """User's active/completed quest instances."""
    __tablename__ = "user_quests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quests.id"), nullable=False)
    status: Mapped[str] = mapped_column(Enum(QuestStatus), nullable=False, default=QuestStatus.ACTIVE)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="quests")
    quest: Mapped["Quest"] = relationship("Quest")
