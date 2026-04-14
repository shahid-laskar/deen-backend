import uuid
from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Text, Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class HabitCategory(str, PyEnum):
    IBADAH    = "ibadah"
    QURAN     = "quran"
    DHIKR     = "dhikr"
    SUNNAH    = "sunnah"
    HEALTH    = "health"
    LEARNING  = "learning"
    PERSONAL  = "personal"
    FAMILY    = "family"
    WORK      = "work"
    FASTING   = "fasting"    # Phase 4
    SADAQAH   = "sadaqah"
    AVOID     = "avoid"


class HabitFrequency(str, PyEnum):
    DAILY              = "daily"
    WEEKDAYS           = "weekdays"
    WEEKENDS           = "weekends"
    CUSTOM             = "custom"
    N_PER_WEEK         = "n_per_week"         # Phase 4
    N_PER_MONTH        = "n_per_month"
    ANCHORED_TO_PRAYER = "anchored_to_prayer"




class HabitType(str, PyEnum):
    BINARY    = "binary"     # done / not done
    QUANTITY  = "quantity"   # count: pages, rakat, cups
    DURATION  = "duration"   # minutes
    AVOID     = "avoid"      # break a bad habit (success = 0 occurrences)
    CHECKLIST = "checklist"  # multi-step; complete = all steps done


class HabitDifficulty(str, PyEnum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"
    EPIC   = "epic"


class AnchorPrayer(str, PyEnum):
    FAJR    = "fajr"
    DHUHR   = "dhuhr"
    ASR     = "asr"
    MAGHRIB = "maghrib"
    ISHA    = "isha"

class Habit(Base, TimestampMixin):
    __tablename__ = "habits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(
        Enum(HabitCategory), nullable=False, default=HabitCategory.PERSONAL
    )
    frequency: Mapped[str] = mapped_column(
        Enum(HabitFrequency), nullable=False, default=HabitFrequency.DAILY
    )
    # Comma-separated day numbers "1,2,3,4,5" for Mon-Fri
    days_of_week: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # "pages", "minutes"
    icon: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)   # emoji
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)   # hex color
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Phase 4 fields ──────────────────────────────────────────────────────
    habit_type: Mapped[str] = mapped_column(
        Enum(HabitType), nullable=False, default=HabitType.BINARY
    )
    difficulty: Mapped[str] = mapped_column(
        Enum(HabitDifficulty), nullable=False, default=HabitDifficulty.MEDIUM
    )
    implementation_intention: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    habit_stack_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    temptation_bundle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    islamic_source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    minimum_version: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    anchor_prayer: Mapped[Optional[str]] = mapped_column(
        Enum(AnchorPrayer), nullable=True
    )
    rahmah_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_token_earned: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="habits")
    logs: Mapped[list["HabitLog"]] = relationship(
        "HabitLog", back_populates="habit", cascade="all, delete-orphan"
    )


class HabitLog(Base, TimestampMixin):
    __tablename__ = "habit_logs"
    __table_args__ = (
        UniqueConstraint("habit_id", "log_date", name="uq_habit_log_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    habit: Mapped["Habit"] = relationship("Habit", back_populates="logs")


# ─── Phase 4: Habit Checklist Item ──────────────────────────────────────────

class HabitChecklistItem(Base, TimestampMixin):
    """Multi-step checklist items for CHECKLIST-type habits."""
    __tablename__ = "habit_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    arabic_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class HabitChecklistLog(Base, TimestampMixin):
    """Per-day completion of each checklist item."""
    __tablename__ = "habit_checklist_logs"
    __table_args__ = (
        UniqueConstraint("item_id", "log_date", name="uq_checklist_log"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habit_checklist_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ─── Phase 4: Dhikr Counter ─────────────────────────────────────────────────

class DhikrType(str, PyEnum):
    SUBHANALLAH          = "subhanallah"
    ALHAMDULILLAH        = "alhamdulillah"
    ALLAHU_AKBAR         = "allahu_akbar"
    LA_ILAHA_ILLALLAH    = "la_ilaha_illallah"
    ISTIGHFAR            = "istighfar"
    SALAWAT              = "salawat"
    SUBHANALLAHI_BIHAMDI = "subhanallahi_bihamdi"
    CUSTOM               = "custom"


class DhikrSession(Base, TimestampMixin):
    """One dhikr counting session."""
    __tablename__ = "dhikr_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    dhikr_type: Mapped[str] = mapped_column(Enum(DhikrType), nullable=False)
    custom_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=33)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
