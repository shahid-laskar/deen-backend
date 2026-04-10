"""
Repository Layer
================
Single import point. Also provides FastAPI dependency injection
helpers so routers can request repositories without touching
AsyncSession directly.

Usage in a router:
    from app.repositories import UserRepo, PrayerRepo

    @router.get("/me")
    async def get_me(
        current_user: CurrentUser,
        user_repo: UserRepo,
    ):
        return await user_repo.get_with_profile_or_404(current_user.id)
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.repositories.prayer import PrayerRepository
from app.repositories.quran import HifzRepository, DuaFavoriteRepository
from app.repositories.habit import HabitRepository, HabitLogRepository
from app.repositories.repos import (
    JournalRepository,
    TaskRepository,
    CycleRepository,
    FastingRepository,
    AIConversationRepository,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "PrayerRepository",
    "HifzRepository",
    "DuaFavoriteRepository",
    "HabitRepository",
    "HabitLogRepository",
    "JournalRepository",
    "TaskRepository",
    "CycleRepository",
    "FastingRepository",
    "AIConversationRepository",
    # DI type aliases
    "UserRepo",
    "PrayerRepo",
    "HifzRepo",
    "DuaFavRepo",
    "HabitRepo",
    "HabitLogRepo",
    "JournalRepo",
    "TaskRepo",
    "CycleRepo",
    "FastingRepo",
    "AIConvRepo",
]

# ─── Dependency factories ─────────────────────────────────────────────────────
# Each returns a repository bound to the request's DB session.

DB = Annotated[AsyncSession, Depends(get_db)]


def get_user_repo(db: DB) -> UserRepository:
    return UserRepository(db)


def get_prayer_repo(db: DB) -> PrayerRepository:
    return PrayerRepository(db)


def get_hifz_repo(db: DB) -> HifzRepository:
    return HifzRepository(db)


def get_dua_fav_repo(db: DB) -> DuaFavoriteRepository:
    return DuaFavoriteRepository(db)


def get_habit_repo(db: DB) -> HabitRepository:
    return HabitRepository(db)


def get_habit_log_repo(db: DB) -> HabitLogRepository:
    return HabitLogRepository(db)


def get_journal_repo(db: DB) -> JournalRepository:
    return JournalRepository(db)


def get_task_repo(db: DB) -> TaskRepository:
    return TaskRepository(db)


def get_cycle_repo(db: DB) -> CycleRepository:
    return CycleRepository(db)


def get_fasting_repo(db: DB) -> FastingRepository:
    return FastingRepository(db)


def get_ai_conv_repo(db: DB) -> AIConversationRepository:
    return AIConversationRepository(db)


# ─── Annotated type aliases for routers ──────────────────────────────────────
# Usage: `user_repo: UserRepo` in a route function signature.

UserRepo       = Annotated[UserRepository,           Depends(get_user_repo)]
PrayerRepo     = Annotated[PrayerRepository,          Depends(get_prayer_repo)]
HifzRepo       = Annotated[HifzRepository,            Depends(get_hifz_repo)]
DuaFavRepo     = Annotated[DuaFavoriteRepository,     Depends(get_dua_fav_repo)]
HabitRepo      = Annotated[HabitRepository,           Depends(get_habit_repo)]
HabitLogRepo   = Annotated[HabitLogRepository,        Depends(get_habit_log_repo)]
JournalRepo    = Annotated[JournalRepository,         Depends(get_journal_repo)]
TaskRepo       = Annotated[TaskRepository,            Depends(get_task_repo)]
CycleRepo      = Annotated[CycleRepository,           Depends(get_cycle_repo)]
FastingRepo    = Annotated[FastingRepository,         Depends(get_fasting_repo)]
AIConvRepo     = Annotated[AIConversationRepository,  Depends(get_ai_conv_repo)]
