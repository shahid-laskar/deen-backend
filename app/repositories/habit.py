"""
Habit Repository
================
All DB access for Habit and HabitLog.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.models.habit import Habit, HabitLog
from app.repositories.base import BaseRepository


class HabitRepository(BaseRepository[Habit]):
    model = Habit

    async def get_all_for_user(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Habit]:
        stmt = select(Habit).where(Habit.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Habit.is_active == True)
        stmt = stmt.order_by(Habit.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_owned_by_user(self, habit_id: UUID, user_id: UUID) -> Habit | None:
        result = await self.db.execute(
            select(Habit).where(
                Habit.id == habit_id,
                Habit.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


class HabitLogRepository(BaseRepository[HabitLog]):
    model = HabitLog

    async def get_for_habit_and_date(
        self, habit_id: UUID, log_date: date
    ) -> HabitLog | None:
        result = await self.db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == habit_id,
                HabitLog.log_date == log_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_habit(
        self, habit_id: UUID, days: int = 90
    ) -> list[HabitLog]:
        start = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == habit_id,
                HabitLog.log_date >= start,
            ).order_by(HabitLog.log_date.desc())
        )
        return list(result.scalars().all())

    async def get_for_user_today(self, user_id: UUID) -> list[HabitLog]:
        result = await self.db.execute(
            select(HabitLog).where(
                HabitLog.user_id == user_id,
                HabitLog.log_date == date.today(),
            )
        )
        return list(result.scalars().all())

    async def upsert(
        self, habit_id: UUID, user_id: UUID, log_date: date, **kwargs
    ) -> HabitLog:
        existing = await self.get_for_habit_and_date(habit_id, log_date)
        if existing:
            for field, value in kwargs.items():
                setattr(existing, field, value)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        return await self.create(
            habit_id=habit_id, user_id=user_id, log_date=log_date, **kwargs
        )
