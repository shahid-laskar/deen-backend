import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class PrayerName(str, PyEnum):
    FAJR = "fajr"
    DHUHR = "dhuhr"
    ASR = "asr"
    MAGHRIB = "maghrib"
    ISHA = "isha"
    JUMUAH = "jumuah"    # Friday prayer (replaces Dhuhr)
    TAHAJJUD = "tahajjud"
    DUHA = "duha"


class PrayerStatus(str, PyEnum):
    ON_TIME = "on_time"
    LATE = "late"
    QADHA = "qadha"          # made up later
    MISSED = "missed"
    EXCUSED = "excused"      # female: during hayd


class PrayerLog(Base, TimestampMixin):
    __tablename__ = "prayer_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "prayer_name", "log_date", name="uq_prayer_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prayer_name: Mapped[str] = mapped_column(Enum(PrayerName), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum(PrayerStatus), nullable=False, default=PrayerStatus.ON_TIME
    )
    prayed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_qadha: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="prayer_logs")
