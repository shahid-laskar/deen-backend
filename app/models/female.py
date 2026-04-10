import uuid
from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


# ─── Fiqh Classifications ──────────────────────────────────────────────────────

class BloodClassification(str, PyEnum):
    """Used for madhab-specific hayd determination."""
    HAYD = "hayd"               # menstrual blood (worship paused)
    TUHR = "tuhr"               # purity period
    ISTIHADAH = "istihadah"     # irregular/abnormal bleeding (worship continues)
    UNCERTAIN = "uncertain"     # user unsure; madhab rule to be applied


class CyclePhase(str, PyEnum):
    HAYD = "hayd"
    TUHR = "tuhr"
    ISTIHADAH = "istihadah"


class MenstrualCycle(Base, TimestampMixin):
    """
    Stores each menstrual cycle entry.
    sensitive fields (symptoms, notes) are AES-256 encrypted.
    madhab_ruling is computed by the fiqh_engine and cached here.
    """
    __tablename__ = "menstrual_cycles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Fiqh engine output
    blood_classification: Mapped[str] = mapped_column(
        Enum(BloodClassification), nullable=False, default=BloodClassification.UNCERTAIN
    )
    hayd_tuhr_status: Mapped[str] = mapped_column(
        Enum(CyclePhase), nullable=False, default=CyclePhase.HAYD
    )
    madhab_ruling: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Worship gates (computed by fiqh engine)
    can_pray: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_fast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_read_quran: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ghusl_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ghusl_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ghusl_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Cycle metadata
    cycle_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    previous_cycle_tuhr_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Encrypted fields (AES-256 per-user key)
    encrypted_notes: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    encrypted_symptoms: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="menstrual_cycles")


# ─── Fasting Log ───────────────────────────────────────────────────────────────

class FastType(str, PyEnum):
    RAMADAN = "ramadan"
    QADHA = "qadha"             # making up missed Ramadan fast
    VOLUNTARY = "voluntary"     # nafl, Monday/Thursday, Muharram etc.
    SHAWWAL = "shawwal"         # 6 days of Shawwal
    ARAFAH = "arafah"
    ASHURA = "ashura"


class MissedReason(str, PyEnum):
    HAYD = "hayd"               # female: menstruation
    NIFAS = "nifas"             # female: post-natal bleeding
    ILLNESS = "illness"
    TRAVEL = "travel"
    FORGOT = "forgot"
    OTHER = "other"


class FastingLog(Base, TimestampMixin):
    """Tracks both intended and missed fasts with qadha planning."""
    __tablename__ = "fasting_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fast_type: Mapped[str] = mapped_column(
        Enum(FastType), nullable=False, default=FastType.RAMADAN
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason_missed: Mapped[Optional[str]] = mapped_column(Enum(MissedReason), nullable=True)
    is_qadha: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_fast_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Fidya / Kaffarah
    fidya_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fidya_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kaffarah_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kaffarah_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="fasting_logs")
