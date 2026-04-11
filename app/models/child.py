"""
Child Upbringing Models
=======================
Child             — child profile
ChildMilestone    — developmental / Islamic milestone
DuaTeachingLog    — track which duas a child has learnt
IslamicLessonLog  — Quran, aqeedah, seerah lesson tracking
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base, TimestampMixin


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

    milestones: Mapped[list["ChildMilestone"]] = relationship(back_populates="child")
    dua_logs: Mapped[list["DuaTeachingLog"]] = relationship(back_populates="child")
    lesson_logs: Mapped[list["IslamicLessonLog"]] = relationship(back_populates="child")


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
    status: Mapped[str] = mapped_column(
        String(20), default="learning"
    )  # not_started, learning, reciting, mastered
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
