import uuid
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class AIContextModule(str, PyEnum):
    GENERAL = "general"
    HABITS = "habits"
    QURAN = "quran"
    JOURNAL = "journal"
    LIFESTYLE = "lifestyle"
    HEALTH = "health"      # nutrition / fitness — never fiqh


class AIConversation(Base, TimestampMixin):
    """
    Each conversation thread per user.
    messages stored as JSON list: [{role, content, timestamp}]
    Capped at AI_DAILY_LIMIT_PER_USER messages/day enforced in service layer.
    """
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    context_module: Mapped[str] = mapped_column(
        Enum(AIContextModule), nullable=False, default=AIContextModule.GENERAL
    )
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True  # false = archived
    )

    user: Mapped["User"] = relationship("User", back_populates="ai_conversations")
