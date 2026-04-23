import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean,  Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
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
    leitner_box: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1-5

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


# ─── Phase 3: Dua Management ─────────────────────────────────────────────────

class Dua(Base, TimestampMixin):
    """
    Seeded dua library — 100+ duas across categories.
    Read-only; users interact via PersonalDua or DuaFavorite.
    """
    __tablename__ = "duas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    arabic_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    transliteration: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    translation: Mapped[str] = mapped_column(String(2000), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Categories: morning_evening, after_prayer, food, travel, distress, guidance,
    #             family, health, forgiveness, protection, gratitude, general
    when_to_recite: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dua_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # within category


class PersonalDua(Base, TimestampMixin):
    """User's own duas — personal prayers they've composed or added."""
    __tablename__ = "personal_duas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(String(3000), nullable=False)
    date_started: Mapped[date] = mapped_column(Date, nullable=False)
    is_answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    answered_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_shared_anonymously: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User")


# ─── Phase 3: Hadith Database ────────────────────────────────────────────────

class HadithCollection(str, PyEnum):
    BUKHARI  = "bukhari"
    MUSLIM   = "muslim"
    ABU_DAWUD = "abu_dawud"
    TIRMIDHI = "tirmidhi"
    NASAI    = "nasai"
    IBN_MAJAH = "ibn_majah"
    MUWATTA  = "muwatta"
    RIYADH_SALIHIN = "riyadh_salihin"


class HadithGrade(str, PyEnum):
    SAHIH  = "sahih"
    HASAN  = "hasan"
    DAIF   = "daif"
    MAWDU  = "mawdu"
    UNKNOWN = "unknown"


class Hadith(Base, TimestampMixin):
    """Seeded hadith records — read-only reference database."""
    __tablename__ = "hadiths"
    __table_args__ = (
        UniqueConstraint("collection", "hadith_number", name="uq_hadith_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection: Mapped[str] = mapped_column(Enum(HadithCollection), nullable=False, index=True)
    book_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    chapter_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hadith_number: Mapped[str] = mapped_column(String(20), nullable=False)
    arabic_text: Mapped[Optional[str]] = mapped_column(String(5000), nullable=True)
    english_text: Mapped[str] = mapped_column(String(5000), nullable=False)
    narrator_chain: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    grade: Mapped[str] = mapped_column(Enum(HadithGrade), nullable=False, default=HadithGrade.UNKNOWN)
    grade_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    topics: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # comma-separated tags


# ─── Phase 3: Quran Reading Log ──────────────────────────────────────────────

class QuranReadingLog(Base, TimestampMixin):
    """Daily reading session log for statistics."""
    __tablename__ = "quran_reading_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    surah_from: Mapped[int] = mapped_column(Integer, nullable=False)
    ayah_from: Mapped[int] = mapped_column(Integer, nullable=False)
    surah_to: Mapped[int] = mapped_column(Integer, nullable=False)
    ayah_to: Mapped[int] = mapped_column(Integer, nullable=False)
    verses_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes_listened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reciter_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="reading")
    # mode: reading | listening | hifz

    user: Mapped["User"] = relationship("User")


# ─── Phase 3: Quran Bookmark ─────────────────────────────────────────────────

class QuranBookmark(Base, TimestampMixin):
    """User bookmarks in the Quran."""
    __tablename__ = "quran_bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    highlight_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # gold|green|blue|red|purple
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookmark_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped["User"] = relationship("User")
    folder: Mapped[Optional["BookmarkFolder"]] = relationship("BookmarkFolder", back_populates="bookmarks")


# ─── Phase 3: Hifz Leitner enhancement ──────────────────────────────────────

# leitner_box lives on HifzProgress (already there)
# Values 1-5; 1 = new/difficult, 5 = mastered


# ─── Lovable Plan: Server-side last-read ────────────────────────────────────

class QuranLastRead(Base, TimestampMixin):
    """Server-side last-read position — syncs across devices."""
    __tablename__ = "quran_last_read"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    surah_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    surah_arabic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_ayahs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship("User")


# ─── Lovable Plan: Bookmark folders ─────────────────────────────────────────

class BookmarkFolder(Base, TimestampMixin):
    """Logical groups for Quran bookmarks."""
    __tablename__ = "bookmark_folders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # e.g. "gold"|"green"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship("User")
    bookmarks: Mapped[list["QuranBookmark"]] = relationship("QuranBookmark", back_populates="folder")


# ─── Lovable Plan: Khatam plans ──────────────────────────────────────────────

class KhatamPlan(Base, TimestampMixin):
    """User-defined plan to complete the Quran by a target date."""
    __tablename__ = "khatam_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    daily_verse_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship("User")
