from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, delete

from app.core.dependencies import CurrentUser, DB
from app.core.security import hash_password, verify_password
from app.models.user import User, UserProfile
from app.schemas.base import MessageResponse
from app.schemas.user import (
    ChangePasswordRequest,
    ProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUser, db: DB):
    """Get current user with profile."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_user(payload: UserUpdateRequest, current_user: CurrentUser, db: DB):
    """Update user settings (gender, madhab, location, timezone)."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/me/profile", response_model=UserResponse)
async def update_profile(payload: ProfileUpdateRequest, current_user: CurrentUser, db: DB):
    """Update display name, avatar, preferences."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.flush()

    # Return full user
    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one()
    return UserResponse.model_validate(user)


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: DB):
    """Change password. Requires current password verification."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses social login. Password change not applicable.",
        )

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    from app.core.security import validate_password_strength
    valid, msg = validate_password_strength(payload.new_password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)

    user.password_hash = hash_password(payload.new_password)
    await db.flush()
    return MessageResponse(message="Password updated successfully.")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(current_user: CurrentUser, db: DB):
    """
    Permanently delete account and all associated data.
    GDPR-compliant: hard delete with cascade.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    await db.delete(user)
    return MessageResponse(message="Account deleted. All your data has been permanently removed.")
