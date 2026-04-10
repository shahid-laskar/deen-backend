"""
Quran Repository
================
All DB access for HifzProgress and DuaFavorite.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.models.quran import HifzProgress, DuaFavorite
from app.repositories.base import BaseRepository


class HifzRepository(BaseRepository[HifzProgress]):
    model = HifzProgress

    async def get_all_for_user(self, user_id: UUID) -> list[HifzProgress]:
        result = await self.db.execute(
            select(HifzProgress)
            .where(HifzProgress.user_id == user_id)
            .order_by(HifzProgress.surah_number, HifzProgress.ayah_from)
        )
        return list(result.scalars().all())

    async def get_due_today(self, user_id: UUID) -> list[HifzProgress]:
        result = await self.db.execute(
            select(HifzProgress).where(
                HifzProgress.user_id == user_id,
                HifzProgress.next_review <= date.today(),
                HifzProgress.status.in_(["in_progress", "memorised", "needs_review"]),
            ).order_by(HifzProgress.next_review)
        )
        return list(result.scalars().all())

    async def get_by_surah_ayah(
        self, user_id: UUID, surah_number: int, ayah_from: int
    ) -> HifzProgress | None:
        result = await self.db.execute(
            select(HifzProgress).where(
                HifzProgress.user_id == user_id,
                HifzProgress.surah_number == surah_number,
                HifzProgress.ayah_from == ayah_from,
            )
        )
        return result.scalar_one_or_none()


class DuaFavoriteRepository(BaseRepository[DuaFavorite]):
    model = DuaFavorite

    async def get_all_for_user(self, user_id: UUID) -> list[DuaFavorite]:
        result = await self.db.execute(
            select(DuaFavorite).where(DuaFavorite.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_key(self, user_id: UUID, dua_key: str) -> DuaFavorite | None:
        result = await self.db.execute(
            select(DuaFavorite).where(
                DuaFavorite.user_id == user_id,
                DuaFavorite.dua_key == dua_key,
            )
        )
        return result.scalar_one_or_none()

    async def key_exists(self, user_id: UUID, dua_key: str) -> bool:
        return await self.get_by_key(user_id, dua_key) is not None
