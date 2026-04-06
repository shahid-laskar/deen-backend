# Import all models so SQLAlchemy registers them with Base.metadata.
# Alembic autogenerate reads this module.

from app.models.user import User, UserProfile, RefreshToken
from app.models.prayer import PrayerLog
from app.models.quran import HifzProgress, DuaFavorite
from app.models.habit import Habit, HabitLog
from app.models.journal import JournalEntry
from app.models.task import Task
from app.models.female import MenstrualCycle, FastingLog
from app.models.ai import AIConversation

__all__ = [
    "User",
    "UserProfile",
    "RefreshToken",
    "PrayerLog",
    "HifzProgress",
    "DuaFavorite",
    "Habit",
    "HabitLog",
    "JournalEntry",
    "Task",
    "MenstrualCycle",
    "FastingLog",
    "AIConversation",
]
