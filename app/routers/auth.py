from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories import UserRepo
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.base import MessageResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DB, user_repo: UserRepo):
    if await user_repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = await user_repo.create(
        email=payload.email,
        password_hash=hash_password(payload.password),
        gender=payload.gender,
        madhab=payload.madhab,
        timezone=payload.timezone,
    )
    await user_repo.upsert_profile(user.id)
    access_token = create_access_token(str(user.id))
    refresh_token_str = create_refresh_token(str(user.id))
    await user_repo.create_refresh_token(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    user = await user_repo.get_with_profile_or_404(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DB, user_repo: UserRepo):
    user = await user_repo.get_by_email(payload.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")
    access_token = create_access_token(str(user.id))
    refresh_token_str = create_refresh_token(str(user.id))
    await user_repo.revoke_all_refresh_tokens(user.id)
    await user_repo.create_refresh_token(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    user = await user_repo.get_with_profile_or_404(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(payload: RefreshRequest, db: DB, user_repo: UserRepo):
    from jose import JWTError
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        user_id = token_data.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    stored = await user_repo.get_refresh_token_by_hash(hash_token(payload.refresh_token))
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked.")
    expires = stored.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token has expired.")
    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: CurrentUser, payload: RefreshRequest, db: DB, user_repo: UserRepo):
    await user_repo.revoke_refresh_token_by_hash(current_user.id, hash_token(payload.refresh_token))
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser, db: DB, user_repo: UserRepo):
    user = await user_repo.get_with_profile_or_404(current_user.id)
    return UserResponse.model_validate(user)
