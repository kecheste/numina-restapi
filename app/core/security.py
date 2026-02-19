from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings

BCRYPT_MAX_PASSWORD_BYTES = 72
BCRYPT_ROUNDS = 12


def _password_bytes(plain_password: str) -> bytes:
    """Encode password to bytes, truncating to 72 bytes for bcrypt."""
    encoded = plain_password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        encoded = encoded[:BCRYPT_MAX_PASSWORD_BYTES]
    return encoded


def hash_password(plain_password: str) -> str:
    """Hash a plain password for storage. Uses bcrypt directly (passlib skipped to avoid init bugs on some platforms)."""
    return bcrypt.hashpw(
        _password_bytes(plain_password),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        _password_bytes(plain_password),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
    subject: str | int,
    *,
    role: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if role is not None:
        payload["role"] = role
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raises InvalidTokenError on failure."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "InvalidTokenError",
]
