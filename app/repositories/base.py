"""
Base Repository
===============
Generic async SQLAlchemy repository.
All model-specific repos inherit from this and gain typed CRUD for free.

Pattern:
    Router  →  Service  →  Repository  →  Database
    (HTTP)     (logic)     (data access)   (SQLAlchemy)

Nothing outside this package should call db.execute() or db.add() directly.
"""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Type-safe async CRUD for any SQLAlchemy model.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User

        repo = UserRepository(db)
        user = await repo.get_or_404(user_id)
    """

    model: Type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Core CRUD ────────────────────────────────────────────────────────────

    async def get(self, id: UUID) -> ModelT | None:
        """Return record by primary key, or None."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_or_404(self, id: UUID, detail: str | None = None) -> ModelT:
        """Return record by primary key, or raise 404."""
        obj = await self.get(id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail or f"{self.model.__name__} not found.",
            )
        return obj

    async def list(
        self,
        *,
        stmt: Select | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by=None,
    ) -> Sequence[ModelT]:
        """
        Return a list of records.
        Pass a custom `stmt` to filter/join; otherwise returns all.
        """
        if stmt is None:
            stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count(self, stmt: Select | None = None) -> int:
        """Count records matching an optional statement."""
        if stmt is None:
            count_stmt = select(func.count()).select_from(self.model)
        else:
            count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and flush a new record. Returns the persisted instance."""
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        """Update fields on an existing instance and flush."""
        for field, value in kwargs.items():
            setattr(obj, field, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_by_id(self, id: UUID, **kwargs: Any) -> ModelT:
        """Update record by id. Raises 404 if not found."""
        obj = await self.get_or_404(id)
        return await self.update(obj, **kwargs)

    async def delete(self, obj: ModelT) -> None:
        """Hard-delete a record."""
        await self.db.delete(obj)
        await self.db.flush()

    async def delete_by_id(self, id: UUID) -> None:
        """Hard-delete by id. Raises 404 if not found."""
        obj = await self.get_or_404(id)
        await self.delete(obj)

    async def exists(self, stmt: Select) -> bool:
        """Return True if any row matches the statement."""
        result = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        return result.scalar_one() > 0

    # ─── Ownership guard ──────────────────────────────────────────────────────

    async def get_owned_or_404(self, id: UUID, user_id: UUID) -> ModelT:
        """
        Return a record that belongs to user_id, or raise 404.
        The model must have a user_id column.
        """
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.user_id == user_id,
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} not found.",
            )
        return obj
