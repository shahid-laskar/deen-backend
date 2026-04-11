from pydantic import EmailStr, field_validator

from app.schemas.base import AppBaseModel
from app.schemas.user import UserResponse


class RegisterRequest(AppBaseModel):
    email: EmailStr
    password: str
    gender: str | None = None
    madhab: str = "hanafi"
    timezone: str = "UTC"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_strength
        valid, msg = validate_password_strength(v)
        if not valid:
            raise ValueError(msg)
        return v

    @field_validator("madhab")
    @classmethod
    def validate_madhab(cls, v: str) -> str:
        valid = {"hanafi", "shafii", "maliki", "hanbali"}
        if v not in valid:
            raise ValueError(f"madhab must be one of {valid}")
        return v


class LoginRequest(AppBaseModel):
    email: EmailStr
    password: str


class TokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(AppBaseModel):
    refresh_token: str


class AccessTokenResponse(AppBaseModel):
    access_token: str
    token_type: str = "bearer"
