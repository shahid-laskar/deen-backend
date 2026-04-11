import hashlib
import hmac
import os
import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings

# ─── Password Hashing (bcrypt direct — avoids passlib/bcrypt version mismatch) ─

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ─── JWT Tokens ────────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": os.urandom(16).hex(),  # unique token ID
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ─── Per-User Encryption (Female Health Data) ─────────────────────────────────
# Each user gets a unique derived key so even if one key leaks, others are safe.

def _derive_user_key(user_id: str) -> bytes:
    """Derive a per-user Fernet key from master key + user_id using HMAC-SHA256."""
    master = settings.ENCRYPTION_MASTER_KEY.encode()
    derived = hmac.new(master, user_id.encode(), hashlib.sha256).digest()
    # Fernet needs 32 bytes → base64url encode
    return base64.urlsafe_b64encode(derived)


def encrypt_field(plaintext: str, user_id: str) -> bytes:
    """Encrypt a string field for storage. Returns ciphertext bytes."""
    if not plaintext:
        return b""
    key = _derive_user_key(user_id)
    f = Fernet(key)
    return f.encrypt(plaintext.encode())


def decrypt_field(ciphertext: bytes, user_id: str) -> str:
    """Decrypt a previously encrypted field. Returns plaintext."""
    if not ciphertext:
        return ""
    key = _derive_user_key(user_id)
    f = Fernet(key)
    return f.decrypt(ciphertext).decode()


# ─── Password Strength Validation ─────────────────────────────────────────────

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    return True, ""
