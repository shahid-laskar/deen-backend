"""
Journal Repository
==================
"""
from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.models.journal import JournalEntry
from app.repositories.base import BaseRepository


class JournalRepository(BaseRepository[JournalEntry]):
    model = JournalEntry

    async def get_for_user(
        self,
        user_id: UUID,
        start: date | None = None,
        end: date | None = None,
        mood: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JournalEntry]:
        stmt = select(JournalEntry).where(JournalEntry.user_id == user_id)
        if start:
            stmt = stmt.where(JournalEntry.entry_date >= start)
        if end:
            stmt = stmt.where(JournalEntry.entry_date <= end)
        if mood:
            stmt = stmt.where(JournalEntry.mood == mood)
        stmt = stmt.order_by(JournalEntry.entry_date.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


"""
Task Repository
===============
"""
from app.models.task import Task


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_for_user(
        self,
        user_id: UUID,
        due_date: date | None = None,
        completed: bool | None = None,
        time_block: str | None = None,
        priority: str | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.user_id == user_id)
        if due_date is not None:
            stmt = stmt.where(Task.due_date == due_date)
        if completed is not None:
            stmt = stmt.where(Task.completed == completed)
        if time_block:
            stmt = stmt.where(Task.time_block == time_block)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        stmt = stmt.order_by(Task.sort_order, Task.due_date, Task.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_due_today(self, user_id: UUID) -> list[Task]:
        return await self.get_for_user(
            user_id, due_date=date.today(), completed=False
        )


"""
Female Repository
=================
"""
from app.models.female import MenstrualCycle, FastingLog


class CycleRepository(BaseRepository[MenstrualCycle]):
    model = MenstrualCycle

    async def get_open_cycle(self, user_id: UUID) -> MenstrualCycle | None:
        result = await self.db.execute(
            select(MenstrualCycle).where(
                MenstrualCycle.user_id == user_id,
                MenstrualCycle.end_date == None,
            )
        )
        return result.scalar_one_or_none()

    async def get_history(
        self, user_id: UUID, limit: int = 12, offset: int = 0
    ) -> list[MenstrualCycle]:
        result = await self.db.execute(
            select(MenstrualCycle)
            .where(MenstrualCycle.user_id == user_id)
            .order_by(MenstrualCycle.start_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_recent_for_fiqh(
        self, user_id: UUID, exclude_id: UUID | None = None, limit: int = 12
    ) -> list[MenstrualCycle]:
        stmt = select(MenstrualCycle).where(MenstrualCycle.user_id == user_id)
        if exclude_id:
            stmt = stmt.where(MenstrualCycle.id != exclude_id)
        stmt = stmt.order_by(MenstrualCycle.start_date.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class FastingRepository(BaseRepository[FastingLog]):
    model = FastingLog

    async def get_for_user(
        self,
        user_id: UUID,
        year: int | None = None,
        fast_type: str | None = None,
    ) -> list[FastingLog]:
        stmt = select(FastingLog).where(FastingLog.user_id == user_id)
        if year:
            stmt = stmt.where(
                FastingLog.fast_date >= date(year, 1, 1),
                FastingLog.fast_date <= date(year, 12, 31),
            )
        if fast_type:
            stmt = stmt.where(FastingLog.fast_type == fast_type)
        stmt = stmt.order_by(FastingLog.fast_date.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_missed_summary(self, user_id: UUID, year: int) -> dict:
        logs = await self.get_for_user(user_id, year=year)
        missed = [l for l in logs if not l.completed and l.fast_type == "ramadan"]
        qadha = [l for l in logs if l.is_qadha and l.completed]
        fidya = [l for l in missed if l.fidya_applicable and not l.fidya_paid]
        return {
            "total_missed": len(missed),
            "total_qadha_made": len(qadha),
            "remaining_qadha": max(0, len(missed) - len(qadha)),
            "fidya_owed": len(fidya),
            "year": year,
        }


"""
AI Repository
=============
"""
from datetime import date as _date

from app.models.ai import AIConversation


class AIConversationRepository(BaseRepository[AIConversation]):
    model = AIConversation

    async def get_active_for_user(
        self, user_id: UUID, limit: int = 20
    ) -> list[AIConversation]:
        result = await self.db.execute(
            select(AIConversation)
            .where(
                AIConversation.user_id == user_id,
                AIConversation.is_active == True,
            )
            .order_by(AIConversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_for_user(self, user_id: UUID) -> list[AIConversation]:
        result = await self.db.execute(
            select(AIConversation).where(AIConversation.user_id == user_id)
        )
        return list(result.scalars().all())

    def count_today_messages(self, conversations: list[AIConversation]) -> int:
        today = _date.today().isoformat()
        return sum(
            1
            for conv in conversations
            for msg in (conv.messages or [])
            if msg.get("role") == "user" and msg.get("date", "") == today
        )
