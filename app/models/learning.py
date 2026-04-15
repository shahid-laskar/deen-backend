"""
Learning Hub models — Phase 9
===============================
Tables: learning_paths, learning_modules, lesson_content, user_learning_progress, vocab_words, user_vocab
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

class Difficulty(str, PyEnum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"

class ContentType(str, PyEnum):
    ARTICLE = "article"
    VIDEO   = "video"
    QUIZ    = "quiz"

class LearningPath(Base, TimestampMixin):
    """A collection of modules (e.g. 'Intro to Fiqh', 'Seerah')."""
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="📚")
    difficulty: Mapped[str] = mapped_column(Enum(Difficulty), nullable=False, default=Difficulty.BEGINNER)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    modules: Mapped[list["LearningModule"]] = relationship("LearningModule", back_populates="path", cascade="all, delete-orphan", order_by="LearningModule.order_index")


class LearningModule(Base, TimestampMixin):
    """A unit of lessons inside a path."""
    __tablename__ = "learning_modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="modules")
    lessons: Mapped[list["LessonContent"]] = relationship("LessonContent", back_populates="module", cascade="all, delete-orphan", order_by="LessonContent.order_index")


class LessonContent(Base, TimestampMixin):
    """Individual lesson content or quiz."""
    __tablename__ = "lesson_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(Enum(ContentType), nullable=False, default=ContentType.ARTICLE)
    content_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # markdown text, or quiz questions
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    module: Mapped["LearningModule"] = relationship("LearningModule", back_populates="lessons")


class UserLearningProgress(Base, TimestampMixin):
    """Tracks which lessons a user has completed."""
    __tablename__ = "user_learning_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lesson_content.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    quiz_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # if content_type is QUIZ

    user: Mapped["User"] = relationship("User")
    lesson: Mapped["LessonContent"] = relationship("LessonContent")


class VocabWord(Base, TimestampMixin):
    """Quranic vocabulary builder word definitions."""
    __tablename__ = "vocab_words"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arabic: Mapped[str] = mapped_column(String(100), nullable=False)
    transliteration: Mapped[str] = mapped_column(String(100), nullable=False)
    translation: Mapped[str] = mapped_column(String(200), nullable=False)
    root_word: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # frequency in Quran


class UserVocab(Base, TimestampMixin):
    """User's Spaced Repetition System (SRS) state for vocab words."""
    __tablename__ = "user_vocab"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    word_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vocab_words.id"), nullable=False)
    box_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 to 5 (Leitner system)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    word: Mapped["VocabWord"] = relationship("VocabWord")
