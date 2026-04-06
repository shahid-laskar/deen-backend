import uuid
from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class HabitCategory(str, PyEnum):
    IBADAH = "ibadah"          # worship-related
    QURAN = "quran"
    DHIKR = "dhikr"
    SUNNAH = "sunnah"
    HEALTH = "health"
    LEARNING = "learning"
    PERSONAL = "personal"
    FAMILY = "family"
    WORK = "work"


class HabitFrequency(str, PyEnum):
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    CUSTOM = "custom"           # specific days of week stored in days_of_week


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
