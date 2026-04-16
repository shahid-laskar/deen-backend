# Import all models so SQLAlchemy registers them with Base.metadata.
# Alembic autogenerate reads this module.

from app.models.user import User, UserProfile, RefreshToken
from app.models.prayer import PrayerLog, IslamicEvent, Mosque
from app.models.quran import HifzProgress, DuaFavorite
from app.models.habit import Habit, HabitLog
from app.models.journal import JournalEntry
from app.models.task import Task
from app.models.female import MenstrualCycle, FastingLog
from app.models.ai import AIConversation
# V2
from app.models.meal import FoodItem, MealPlan, MealEntry
from app.models.workout import Exercise, WorkoutPlan, WorkoutSession
from app.models.child import Child, ChildMilestone, DuaTeachingLog, IslamicLessonLog
from app.models.recitation import RecitationSession, RecitationFeedback
# V3
from app.models.community import (
    CommunityGroup, GroupMember, Post, Comment, PostReaction,
    ContentReport, WaqfProject, Donation,
    Topic, ScholarProfile, QAQuestion, QAAnswer,
    AccountabilityCircle, CircleMember, CircleGoal, CircleCheckIn,
    Halaqah, HalaqahSession, HalaqahNote
)
from app.models.finance import ZakatCalculation, ZakatReminder, VettedCharity
from app.models.family import FamilyPlan, FamilyMember
# Phase 7 — Gamification
from app.models.gamification import UserXP, Badge, UserBadge, Quest, UserQuest
# Phase 9 — Learning
from app.models.learning import LearningPath, LearningModule, LessonContent, UserLearningProgress, VocabWord, UserVocab
from app.models.health import WaterLog, SleepLog

__all__ = [
    "User", "UserProfile", "RefreshToken",
    "PrayerLog",
    "HifzProgress", "DuaFavorite",
    "Habit", "HabitLog",
    "JournalEntry",
    "Task",
    "MenstrualCycle", "FastingLog",
    "AIConversation",
    # V2
    "FoodItem", "MealPlan", "MealEntry",
    "Exercise", "WorkoutPlan", "WorkoutSession",
    "Child", "ChildMilestone", "DuaTeachingLog", "IslamicLessonLog",
    "RecitationSession", "RecitationFeedback",
    # V3
    "CommunityGroup", "GroupMember", "Post", "Comment", "PostReaction",
    "ContentReport", "WaqfProject", "Donation",
    "Topic", "ScholarProfile", "QAQuestion", "QAAnswer",
    "AccountabilityCircle", "CircleMember", "CircleGoal", "CircleCheckIn",
    "Halaqah", "HalaqahSession", "HalaqahNote",
    "ZakatCalculation", "ZakatReminder", "VettedCharity",
    "FamilyPlan", "FamilyMember"
]
