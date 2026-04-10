import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class HifzStatus(str, PyEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    MEMORISED = "memorised"
    NEEDS_REVIEW = "needs_review"


class HifzProgress(Base, TimestampMixin):
    """
    Tracks Quran memorisation per surah/ayah range.
    Uses spaced repetition: ease_factor drives next_review scheduling.
    """
    __tablename__ = "hifz_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "surah_number", "ayah_from", name="uq_hifz_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    surah_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ayah_from: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ayah_to: Mapped[int] = mapped_column(Integer, nullable=False)
    total_ayahs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        Enum(HifzStatus), nullable=False, default=HifzStatus.NOT_STARTED
    )
    last_reviewed: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_review: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ease_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5  # SM-2 algorithm starting value
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    user: Mapped["User"] = relationship("User", back_populates="hifz_progress")


class DuaFavorite(Base, TimestampMixin):
    """User-saved duas. dua_key references the static dua dataset."""
    __tablename__ = "dua_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "dua_key", name="uq_dua_favorite"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dua_key: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    custom_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="dua_favorites")
