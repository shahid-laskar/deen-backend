"""
Prayer Repository
=================
All DB access for PrayerLog.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select, and_

from app.models.prayer import PrayerLog
from app.repositories.base import BaseRepository


class PrayerRepository(BaseRepository[PrayerLog]):
    model = PrayerLog

    async def get_by_prayer_and_date(
        self, user_id: UUID, prayer_name: str, log_date: date
    ) -> PrayerLog | None:
        result = await self.db.execute(
            select(PrayerLog).where(
                PrayerLog.user_id == user_id,
                PrayerLog.prayer_name == prayer_name,
                PrayerLog.log_date == log_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_date_range(
        self, user_id: UUID, start: date, end: date
    ) -> list[PrayerLog]:
        result = await self.db.execute(
            select(PrayerLog).where(
                PrayerLog.user_id == user_id,
                PrayerLog.log_date >= start,
                PrayerLog.log_date <= end,
            ).order_by(PrayerLog.log_date.desc(), PrayerLog.prayer_name)
        )
        return list(result.scalars().all())

    async def get_today(self, user_id: UUID) -> list[PrayerLog]:
        return await self.get_for_date_range(user_id, date.today(), date.today())

    async def get_for_streak(self, user_id: UUID, days: int = 90) -> list[PrayerLog]:
        start = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(PrayerLog).where(
                PrayerLog.user_id == user_id,
                PrayerLog.log_date >= start,
                PrayerLog.prayer_name.in_(['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']),
            )
        )
        return list(result.scalars().all())

    async def upsert(self, user_id: UUID, **kwargs) -> PrayerLog:
        """Insert or update a prayer log for a given prayer + date."""
        existing = await self.get_by_prayer_and_date(
            user_id,
            kwargs['prayer_name'],
            kwargs['log_date'],
        )
        if existing:
            for field, value in kwargs.items():
                setattr(existing, field, value)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        return await self.create(user_id=user_id, **kwargs)
