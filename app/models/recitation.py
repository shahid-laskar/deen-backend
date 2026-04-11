"""
Quran Recitation Models
=======================
RecitationSession — a practice / assessment session
RecitationFeedback — AI-generated tajweed feedback per session
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base, TimestampMixin


class RecitationSession(Base, TimestampMixin):
    __tablename__ = "recitation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    surah_number: Mapped[int | None] = mapped_column(Integer)
    surah_name: Mapped[str | None] = mapped_column(String(100))
    ayah_from: Mapped[int | None] = mapped_column(Integer)
    ayah_to: Mapped[int | None] = mapped_column(Integer)
    recited_text: Mapped[str | None] = mapped_column(Text)  # transcribed from audio

    # Audio (stored externally, URL reference only)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Scores (0-100)
    overall_score: Mapped[float | None] = mapped_column(Float)
    fluency_score: Mapped[float | None] = mapped_column(Float)
    tajweed_score: Mapped[float | None] = mapped_column(Float)
    pronunciation_score: Mapped[float | None] = mapped_column(Float)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, complete, failed

    session_type: Mapped[str] = mapped_column(
        String(20), default="practice"
    )  # practice, assessment, memorisation

    user_rating: Mapped[int | None] = mapped_column(Integer)  # self-rating 1-5
    notes: Mapped[str | None] = mapped_column(Text)

    feedback: Mapped["RecitationFeedback | None"] = relationship(back_populates="session", uselist=False)


class RecitationFeedback(Base, TimestampMixin):
    __tablename__ = "recitation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recitation_sessions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Structured feedback
    tajweed_errors: Mapped[list | None] = mapped_column(JSON)
    # [{type: "madd_error", ayah: 3, word: "الرحمن", suggestion: "extend madd 2 counts"}]
    strengths: Mapped[list | None] = mapped_column(JSON)  # ["good makharij", "clear qalqalah"]
    improvement_areas: Mapped[list | None] = mapped_column(JSON)
    next_steps: Mapped[str | None] = mapped_column(Text)

    # Full AI commentary
    summary: Mapped[str | None] = mapped_column(Text)
    detailed_feedback: Mapped[str | None] = mapped_column(Text)

    # Source
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    transcription_confidence: Mapped[float | None] = mapped_column(Float)

    session: Mapped["RecitationSession"] = relationship(back_populates="feedback")
