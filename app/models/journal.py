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
