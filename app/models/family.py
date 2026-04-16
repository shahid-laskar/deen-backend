"""
Family Accounts Models
======================
FamilyPlan — representing a family grouping
FamilyMember — representing a user within a family plan and their role
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

class FamilyPlan(Base, TimestampMixin):
    __tablename__ = "family_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    plan_type: Mapped[str] = mapped_column(String(50), default="standard")
    member_count: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    members: Mapped[list["FamilyMember"]] = relationship(back_populates="family")


class FamilyMember(Base, TimestampMixin):
    __tablename__ = "family_members"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member") # admin, member
    account_type: Mapped[str] = mapped_column(String(20), default="adult") # adult, teen, child
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped["FamilyPlan"] = relationship(back_populates="members")
