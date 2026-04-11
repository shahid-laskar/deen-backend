"""
Workout Planner Models
======================
WorkoutPlan     — template plan (e.g. "Ramadan strength programme")
WorkoutSession  — a logged workout on a specific date
Exercise        — reusable exercise catalogue entry
SessionExercise — junction: which exercises appear in a session + sets/reps
"""

import uuid
from datetime import date, time

from sqlalchemy import (
    Boolean, Date, Float, ForeignKey, Integer,
    String, Text, Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base, TimestampMixin


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # None = global

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    arabic_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String(50), default="strength"
    )  # strength, cardio, flexibility, calisthenics, martial_arts, sport
    muscle_groups: Mapped[list | None] = mapped_column(JSON)  # ["chest", "triceps"]
    equipment: Mapped[str | None] = mapped_column(String(100))  # none, dumbbell, barbell, mat

    # Islamic compatibility
    is_wudu_safe: Mapped[bool] = mapped_column(Boolean, default=True)
    # wudu_safe = won't break wudu (no contact sports sweat issues etc.)
    gender_suitable: Mapped[str] = mapped_column(String(20), default="all")  # all, male, female
    notes: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))


class WorkoutPlan(Base, TimestampMixin):
    __tablename__ = "workout_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(String(100))  # strength, weight_loss, endurance, flexibility
    days_per_week: Mapped[int] = mapped_column(Integer, default=3)
    duration_weeks: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_ramadan_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_time_block: Mapped[str | None] = mapped_column(String(30))  # after_fajr, after_asr, after_isha

    sessions: Mapped[list["WorkoutSession"]] = relationship(back_populates="plan")


class WorkoutSession(Base, TimestampMixin):
    __tablename__ = "workout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workout_plans.id", ondelete="SET NULL"), nullable=True
    )

    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_name: Mapped[str | None] = mapped_column(String(200))
    start_time: Mapped[time | None] = mapped_column(Time)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    calories_burned: Mapped[float | None] = mapped_column(Float)
    heart_rate_avg: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5

    # Flexible exercise log stored as JSON
    # [{exercise_id, exercise_name, sets: [{reps, weight_kg, duration_s, rest_s}]}]
    exercises_log: Mapped[list | None] = mapped_column(JSON)

    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    time_block: Mapped[str | None] = mapped_column(String(30))

    plan: Mapped["WorkoutPlan | None"] = relationship(back_populates="sessions")
