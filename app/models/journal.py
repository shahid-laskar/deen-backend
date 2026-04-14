import uuid
from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Mood(str, PyEnum):
    GRATEFUL = "grateful"
    PEACEFUL = "peaceful"
    HOPEFUL = "hopeful"
    MOTIVATED = "motivated"
    REFLECTIVE = "reflective"
    ANXIOUS = "anxious"
    SAD = "sad"
    OVERWHELMED = "overwhelmed"
    NEUTRAL = "neutral"


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[Optional[str]] = mapped_column(Enum(Mood), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gratitude: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intentions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quran_ayah_ref: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="journal_entries")


class JournalMode(str, PyEnum):
    FREE_WRITE         = "free_write"
    GUIDED_REFLECTION  = "guided_reflection"
    MUHASABAH          = "muhasabah"
    WEEKLY_REVIEW      = "weekly_review"
    GRATITUDE          = "gratitude"


# Extend JournalEntry — Phase 5 fields added via new columns
# linter-friendly: add columns after existing ones in migration
# We monkey-patch here so SQLAlchemy sees them.

from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import JSON as _JSON

# Inject columns into JournalEntry class
import uuid as _uuid

JournalEntry.journal_mode     = mapped_column(
    Enum(JournalMode), nullable=True, default=JournalMode.FREE_WRITE
)
JournalEntry.muhasabah_data   = mapped_column(_JSON, nullable=True)
JournalEntry.gratitude_items  = mapped_column(_JSON, nullable=True)
JournalEntry.weekly_data      = mapped_column(_JSON, nullable=True)
JournalEntry.ai_prompt_used   = mapped_column(String(500), nullable=True)
# E2E encryption fields — when is_encrypted=True, content holds ciphertext (base64)
JournalEntry.is_encrypted     = mapped_column(Boolean, nullable=False, default=False)
JournalEntry.iv               = mapped_column(String(100), nullable=True)   # base64 96-bit IV
JournalEntry.salt             = mapped_column(String(100), nullable=True)   # base64 salt


# ─── Phase 5: Daily Insight ─────────────────────────────────────────────────

class InsightCategory(str, PyEnum):
    PRAYER_PATTERNS  = "prayer_patterns"
    QURAN_PATTERNS   = "quran_patterns"
    HABIT_CORRELATIONS = "habit_correlations"
    SPIRITUAL_TRENDS = "spiritual_trends"
    MOOD_JOURNAL     = "mood_journal"


class DailyInsight(Base, TimestampMixin):
    """AI-generated daily personalised insight. One active per user per day."""
    __tablename__ = "daily_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Enum(InsightCategory), nullable=False)
    relevant_ayah: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    relevant_hadith: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 1 = Helpful, -1 = Not relevant, 0 = no rating
    user_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship("User")


# ─── Phase 5: Monthly Letter ─────────────────────────────────────────────────

class MonthlyLetter(Base, TimestampMixin):
    """End-of-month AI-generated reflective summary."""
    __tablename__ = "monthly_letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)   # 1-12
    letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    mood_summary: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    top_themes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship("User")
