"""
User Repository
===============
DB access for User, UserProfile, RefreshToken, DevicePushToken.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.user import User, UserProfile, RefreshToken, DevicePushToken
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    # ─── Lookups ──────────────────────────────────────────────────────────────

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_profile(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_with_profile_or_404(self, user_id: UUID) -> User:
        user = await self.get_with_profile(user_id)
        if user is None:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    # ─── Profile ──────────────────────────────────────────────────────────────

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: UUID, **kwargs) -> UserProfile:
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id, **kwargs)
            self.db.add(profile)
        else:
            for field, value in kwargs.items():
                setattr(profile, field, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # ─── Refresh tokens ───────────────────────────────────────────────────────

    async def create_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        device_id: Optional[str] = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_id=device_id,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
            )
        )
        return result.scalar_one_or_none()

    async def revoke_all_refresh_tokens(self, user_id: UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )

    async def revoke_refresh_token_by_hash(self, user_id: UUID, token_hash: str) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.token_hash == token_hash)
            .values(is_revoked=True)
        )

    async def revoke_refresh_token_by_device(self, user_id: UUID, device_id: str) -> None:
        """Revoke all refresh tokens for this user+device pair (for per-device login)."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.device_id == device_id,
                RefreshToken.is_revoked == False,
            )
            .values(is_revoked=True)
        )

    # ─── Device push tokens ───────────────────────────────────────────────────

    async def upsert_device_push_token(
        self,
        user_id: UUID,
        push_token: str,
        platform: str,
        device_id: Optional[str] = None,
    ) -> DevicePushToken:
        """Insert or update a FCM/APNs push token. Idempotent per device_id."""
        existing = None
        if device_id:
            result = await self.db.execute(
                select(DevicePushToken).where(DevicePushToken.device_id == device_id)
            )
            existing = result.scalar_one_or_none()

        if existing:
            existing.push_token = push_token
            existing.platform = platform
            existing.user_id = user_id
            existing.is_active = True
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        token = DevicePushToken(
            user_id=user_id,
            push_token=push_token,
            platform=platform,
            device_id=device_id,
        )
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token
