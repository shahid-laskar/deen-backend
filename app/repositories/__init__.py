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

# ─── V2 + V3 repositories ──────────────────────────────────────────────────────
from app.repositories.v2 import (
    FoodItemRepository, MealPlanRepository, MealEntryRepository,
    ExerciseRepository, WorkoutPlanRepository, WorkoutSessionRepository,
    ChildRepository, MilestoneRepository, DuaTeachingRepository, LessonLogRepository,
    RecitationRepository, RecitationFeedbackRepository,
    CommunityGroupRepository, PostRepository, CommentRepository,
    WaqfProjectRepository, DonationRepository,
)

def get_food_item_repo(db: DB) -> FoodItemRepository:       return FoodItemRepository(db)
def get_meal_plan_repo(db: DB) -> MealPlanRepository:       return MealPlanRepository(db)
def get_meal_entry_repo(db: DB) -> MealEntryRepository:     return MealEntryRepository(db)
def get_exercise_repo(db: DB) -> ExerciseRepository:         return ExerciseRepository(db)
def get_workout_plan_repo(db: DB) -> WorkoutPlanRepository:  return WorkoutPlanRepository(db)
def get_workout_session_repo(db: DB) -> WorkoutSessionRepository: return WorkoutSessionRepository(db)
def get_child_repo(db: DB) -> ChildRepository:               return ChildRepository(db)
def get_milestone_repo(db: DB) -> MilestoneRepository:       return MilestoneRepository(db)
def get_dua_teaching_repo(db: DB) -> DuaTeachingRepository:  return DuaTeachingRepository(db)
def get_lesson_log_repo(db: DB) -> LessonLogRepository:      return LessonLogRepository(db)
def get_recitation_repo(db: DB) -> RecitationRepository:     return RecitationRepository(db)
def get_recitation_feedback_repo(db: DB) -> RecitationFeedbackRepository: return RecitationFeedbackRepository(db)
def get_community_group_repo(db: DB) -> CommunityGroupRepository: return CommunityGroupRepository(db)
def get_post_repo(db: DB) -> PostRepository:                  return PostRepository(db)
def get_comment_repo(db: DB) -> CommentRepository:            return CommentRepository(db)
def get_waqf_project_repo(db: DB) -> WaqfProjectRepository:  return WaqfProjectRepository(db)
def get_donation_repo(db: DB) -> DonationRepository:          return DonationRepository(db)

FoodItemRepo        = Annotated[FoodItemRepository,          Depends(get_food_item_repo)]
MealPlanRepo        = Annotated[MealPlanRepository,          Depends(get_meal_plan_repo)]
MealEntryRepo       = Annotated[MealEntryRepository,         Depends(get_meal_entry_repo)]
ExerciseRepo        = Annotated[ExerciseRepository,           Depends(get_exercise_repo)]
WorkoutPlanRepo     = Annotated[WorkoutPlanRepository,        Depends(get_workout_plan_repo)]
WorkoutSessionRepo  = Annotated[WorkoutSessionRepository,     Depends(get_workout_session_repo)]
ChildRepo           = Annotated[ChildRepository,              Depends(get_child_repo)]
MilestoneRepo       = Annotated[MilestoneRepository,          Depends(get_milestone_repo)]
DuaTeachingRepo     = Annotated[DuaTeachingRepository,        Depends(get_dua_teaching_repo)]
LessonLogRepo       = Annotated[LessonLogRepository,          Depends(get_lesson_log_repo)]
RecitationRepo      = Annotated[RecitationRepository,         Depends(get_recitation_repo)]
RecitationFbRepo    = Annotated[RecitationFeedbackRepository, Depends(get_recitation_feedback_repo)]
CommunityGroupRepo  = Annotated[CommunityGroupRepository,     Depends(get_community_group_repo)]
PostRepo            = Annotated[PostRepository,               Depends(get_post_repo)]
CommentRepo         = Annotated[CommentRepository,            Depends(get_comment_repo)]
WaqfProjectRepo     = Annotated[WaqfProjectRepository,        Depends(get_waqf_project_repo)]
DonationRepo        = Annotated[DonationRepository,           Depends(get_donation_repo)]
