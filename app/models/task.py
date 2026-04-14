import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class TaskPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskCategory(str, PyEnum):
    WORK = "work"
    PERSONAL = "personal"
    IBADAH = "ibadah"
    FAMILY = "family"
    HEALTH = "health"
    LEARNING = "learning"
    ERRAND = "errand"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Enum(TaskCategory), nullable=True)
    priority: Mapped[str] = mapped_column(
        Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    # Time blocks: "after_fajr", "morning", "after_dhuhr", "afternoon",
    #              "after_asr", "evening", "after_maghrib", "after_isha"
    time_block: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True  # for sub-tasks
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Phase 4 additions
    islamic_context: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linked_habit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="SET NULL"), nullable=True
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship("User", back_populates="tasks")
