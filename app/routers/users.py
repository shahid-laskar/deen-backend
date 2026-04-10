from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DB
from app.core.security import hash_password, verify_password
from app.repositories import UserRepo
from app.schemas.base import MessageResponse
from app.schemas.user import (
    ChangePasswordRequest,
    ProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUser, db: DB, user_repo: UserRepo):
    user = await user_repo.get_with_profile_or_404(current_user.id)
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_user(payload: UserUpdateRequest, current_user: CurrentUser, db: DB, user_repo: UserRepo):
    user = await user_repo.update(current_user, **payload.model_dump(exclude_none=True))
    user = await user_repo.get_with_profile_or_404(user.id)
    return UserResponse.model_validate(user)


@router.patch("/me/profile", response_model=UserResponse)
async def update_profile(payload: ProfileUpdateRequest, current_user: CurrentUser, db: DB, user_repo: UserRepo):
    await user_repo.upsert_profile(current_user.id, **payload.model_dump(exclude_none=True))
    user = await user_repo.get_with_profile_or_404(current_user.id)
    return UserResponse.model_validate(user)


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: DB, user_repo: UserRepo):
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="This account uses social login.")
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    from app.core.security import validate_password_strength
    valid, msg = validate_password_strength(payload.new_password)
    if not valid:
        raise HTTPException(status_code=422, detail=msg)
    await user_repo.update(current_user, password_hash=hash_password(payload.new_password))
    return MessageResponse(message="Password updated successfully.")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(current_user: CurrentUser, db: DB, user_repo: UserRepo):
    await user_repo.delete(current_user)
    return MessageResponse(message="Account deleted. All your data has been permanently removed.")
