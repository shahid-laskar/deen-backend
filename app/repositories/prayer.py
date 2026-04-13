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

    async def get_stats_30d(self, user_id: UUID) -> list[dict]:
        """Per-prayer stats for the last 30 days."""
        from datetime import timedelta
        from sqlalchemy import func, case
        start = date.today() - timedelta(days=30)
        result = await self.db.execute(
            select(
                PrayerLog.prayer_name,
                func.count().label("total"),
                func.sum(case((PrayerLog.status == "on_time", 1), else_=0)).label("on_time"),
                func.sum(case((PrayerLog.status == "late", 1), else_=0)).label("late"),
                func.sum(case((PrayerLog.status == "missed", 1), else_=0)).label("missed"),
                func.sum(case((PrayerLog.status == "qadha", 1), else_=0)).label("qadha"),
                func.sum(case((PrayerLog.with_congregation == True, 1), else_=0)).label("congregation"),
                func.avg(PrayerLog.khushu_rating).label("avg_khushu"),
            ).where(
                PrayerLog.user_id == user_id,
                PrayerLog.log_date >= start,
                PrayerLog.prayer_name.in_(["fajr", "dhuhr", "asr", "maghrib", "isha"]),
            ).group_by(PrayerLog.prayer_name)
        )
        return [dict(r._mapping) for r in result.all()]

    async def get_heatmap(self, user_id: UUID, days: int = 365) -> list[dict]:
        """52-week heatmap: daily count + on-time count."""
        from datetime import timedelta
        from sqlalchemy import func, case
        start = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(
                PrayerLog.log_date,
                func.count().label("count"),
                func.sum(case((PrayerLog.status == "on_time", 1), else_=0)).label("on_time"),
            ).where(
                PrayerLog.user_id == user_id,
                PrayerLog.log_date >= start,
                PrayerLog.prayer_name.in_(["fajr", "dhuhr", "asr", "maghrib", "isha"]),
            ).group_by(PrayerLog.log_date).order_by(PrayerLog.log_date)
        )
        return [dict(r._mapping) for r in result.all()]

    async def get_weekly_summary(self, user_id: UUID) -> dict:
        """Summary for the current ISO week."""
        from datetime import timedelta
        from sqlalchemy import func, case
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        days_elapsed = today.weekday() + 1
        result = await self.db.execute(
            select(
                PrayerLog.prayer_name,
                func.sum(case((PrayerLog.status == "on_time", 1), else_=0)).label("on_time"),
                func.sum(case((PrayerLog.status.in_(["on_time", "late"]), 1), else_=0)).label("prayed"),
                func.sum(case((PrayerLog.with_congregation == True, 1), else_=0)).label("congregation"),
                func.count().label("total"),
            ).where(
                PrayerLog.user_id == user_id,
                PrayerLog.log_date >= week_start,
                PrayerLog.log_date <= today,
                PrayerLog.prayer_name.in_(["fajr", "dhuhr", "asr", "maghrib", "isha"]),
            ).group_by(PrayerLog.prayer_name)
        )
        rows = [dict(r._mapping) for r in result.all()]
        total_on_time = sum(r["on_time"] for r in rows)
        total_prayed  = sum(r["prayed"]  for r in rows)
        total_congregation = sum(r["congregation"] for r in rows)
        possible = days_elapsed * 5
        by_name = {r["prayer_name"]: r for r in rows}
        best  = max(by_name, key=lambda k: by_name[k]["on_time"], default=None) if by_name else None
        worst = min(by_name, key=lambda k: by_name[k]["on_time"], default=None) if by_name else None
        return {
            "week_start": week_start, "week_end": week_end,
            "total_prayers_possible": possible,
            "total_prayed": total_prayed, "total_on_time": total_on_time,
            "on_time_pct": round((total_on_time / possible) * 100, 1) if possible else 0,
            "congregation_count": total_congregation,
            "best_prayer": best, "worst_prayer": worst,
        }


# ─── Islamic Events Repository ───────────────────────────────────────────────

from app.models.prayer import IslamicEvent as _IslamicEvent


class IslamicEventRepository(BaseRepository[_IslamicEvent]):
    model = _IslamicEvent

    async def get_all(self) -> list[_IslamicEvent]:
        result = await self.db.execute(select(_IslamicEvent).order_by(_IslamicEvent.hijri_month, _IslamicEvent.hijri_day))
        return list(result.scalars().all())

    async def get_by_type(self, event_type: str) -> list[_IslamicEvent]:
        result = await self.db.execute(
            select(_IslamicEvent).where(_IslamicEvent.event_type == event_type)
        )
        return list(result.scalars().all())

    async def get_current_events(self, hijri_month: int, hijri_day: int) -> list[_IslamicEvent]:
        """Events whose window covers today's Hijri date."""
        result = await self.db.execute(
            select(_IslamicEvent).where(_IslamicEvent.hijri_month == hijri_month)
        )
        events = list(result.scalars().all())
        return [
            e for e in events
            if e.hijri_day <= hijri_day < (e.hijri_day + e.duration_days)
        ]
