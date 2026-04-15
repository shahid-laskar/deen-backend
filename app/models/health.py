"""
Health tracker models — Phase 9
===============================
Tables: water_logs, sleep_logs
"""
import uuid
from datetime import date as DateType, time as TimeType

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

class WaterLog(Base, TimestampMixin):
    """Daily water consumption tracker."""
    __tablename__ = "water_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[DateType] = mapped_column(Date, nullable=False, index=True)
    cups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goal: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    user: Mapped["User"] = relationship("User")


class SleepLog(Base, TimestampMixin):
    """Sleep cycle and quality tracker."""
    __tablename__ = "sleep_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[DateType] = mapped_column(Date, nullable=False, index=True)
    bedtime: Mapped[TimeType] = mapped_column(Time, nullable=False)
    wake_time: Mapped[TimeType] = mapped_column(Time, nullable=False)
    quality_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5

    user: Mapped["User"] = relationship("User")
