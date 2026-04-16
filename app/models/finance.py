"""
Islamic Finance Models
======================
ZakatCalculation — tracks user's historical zakat calculations
ZakatReminder — keeps track of the hawl date for notifications
VettedCharity — lists verified charitable organizations for directory
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base, TimestampMixin

class ZakatCalculation(Base, TimestampMixin):
    __tablename__ = "zakat_calculations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    hijri_year: Mapped[str | None] = mapped_column(String(20))
    nisab_standard: Mapped[str] = mapped_column(String(20), default="gold") # gold, silver
    
    # JSON fields to store the state of assets and liabilities at the time of calculation
    assets: Mapped[dict | None] = mapped_column(JSON)
    liabilities: Mapped[dict | None] = mapped_column(JSON)
    
    # The output amounts
    net_zakatable_assets: Mapped[float] = mapped_column(Float, default=0.0)
    zakat_due: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")


class ZakatReminder(Base, TimestampMixin):
    __tablename__ = "zakat_reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hawl_date: Mapped[date] = mapped_column(Date, nullable=False) # The lunar anniversary date
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VettedCharity(Base, TimestampMixin):
    __tablename__ = "vetted_charities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(100))
    causes: Mapped[list | None] = mapped_column(JSON) # e.g. ["education", "water", "orphan"]
    is_zakat_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    stripe_account: Mapped[str | None] = mapped_column(String(100))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))
