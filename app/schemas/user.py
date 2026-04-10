from typing import Optional
from uuid import UUID

from pydantic import EmailStr

from app.schemas.base import AppBaseModel, IDSchema, TimestampSchema


class UserProfileResponse(AppBaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    quran_daily_goal_minutes: int = 15
    notifications_enabled: bool = True
    prayer_notifications: bool = True
    habit_reminder_time: Optional[str] = None


class UserResponse(IDSchema, TimestampSchema):
    email: str
    gender: Optional[str] = None
    madhab: str
    timezone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    prayer_method: Optional[str] = None
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    profile: Optional[UserProfileResponse] = None


class UserUpdateRequest(AppBaseModel):
    gender: Optional[str] = None
    madhab: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    prayer_method: Optional[str] = None
    onboarding_completed: Optional[bool] = None


class ProfileUpdateRequest(AppBaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    quran_daily_goal_minutes: Optional[int] = None
    notifications_enabled: Optional[bool] = None
    prayer_notifications: Optional[bool] = None
    habit_reminder_time: Optional[str] = None


class ChangePasswordRequest(AppBaseModel):
    current_password: str
    new_password: str
