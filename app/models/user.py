import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Gender(str, PyEnum):
    MALE = "male"
    FEMALE = "female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Madhab(str, PyEnum):
    HANAFI = "hanafi"
    SHAFII = "shafii"
    MALIKI = "maliki"
    HANBALI = "hanbali"


class PrayerMethod(str, PyEnum):
    """Calculation methods for prayer times."""
    MUSLIM_WORLD_LEAGUE = "Muslim World League"
    ISNA = "Islamic Society of North America"
    EGYPT = "Egyptian General Authority of Survey"
    MAKKAH = "Umm Al-Qura University, Makkah"
    KARACHI = "University of Islamic Sciences, Karachi"
    TEHRAN = "Institute of Geophysics, University of Tehran"
    SINGAPORE = "Majlis Ugama Islam Singapura"
    TURKEY = "Diyanet İşleri Başkanlığı, Turkey"
    FRANCE = "Union des organisations islamiques de France"
    RUSSIA = "Spiritual Administration of Muslims of Russia"
    GULF = "Gulf Region"
    KUWAIT = "Kuwait"
    QATAR = "Qatar"
    SINGAPORE_2 = "Majlis Ugama Islam Singapura"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(
        Enum(Gender), nullable=True
    )
    madhab: Mapped[str] = mapped_column(
        Enum(Madhab), nullable=False, default=Madhab.HANAFI
    )
    timezone: Mapped[str] = mapped_column(
        String(100), nullable=False, default="UTC"
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prayer_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    prayer_logs: Mapped[list["PrayerLog"]] = relationship(
        "PrayerLog", back_populates="user", cascade="all, delete-orphan"
    )
    habits: Mapped[list["Habit"]] = relationship(
        "Habit", back_populates="user", cascade="all, delete-orphan"
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        "JournalEntry", back_populates="user", cascade="all, delete-orphan"
    )
    hifz_progress: Mapped[list["HifzProgress"]] = relationship(
        "HifzProgress", back_populates="user", cascade="all, delete-orphan"
    )
    dua_favorites: Mapped[list["DuaFavorite"]] = relationship(
        "DuaFavorite", back_populates="user", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )
    menstrual_cycles: Mapped[list["MenstrualCycle"]] = relationship(
        "MenstrualCycle", back_populates="user", cascade="all, delete-orphan"
    )
    fasting_logs: Mapped[list["FastingLog"]] = relationship(
        "FastingLog", back_populates="user", cascade="all, delete-orphan"
    )
    ai_conversations: Mapped[list["AIConversation"]] = relationship(
        "AIConversation", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    # Phase 7 — Gamification
    xp_events: Mapped[list["UserXP"]] = relationship(
        "UserXP", back_populates="user", cascade="all, delete-orphan"
    )
    badges: Mapped[list["UserBadge"]] = relationship(
        "UserBadge", back_populates="user", cascade="all, delete-orphan"
    )
    quests: Mapped[list["UserQuest"]] = relationship(
        "UserQuest", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quran_daily_goal_minutes: Mapped[int] = mapped_column(nullable=False, default=15)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prayer_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    habit_reminder_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # "20:00"

    # Phase 1 additions
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    spiritual_archetype: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # Values: scholar | devotee | seeker | guardian | servant
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default='en')

    user: Mapped["User"] = relationship("User", back_populates="profile")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
