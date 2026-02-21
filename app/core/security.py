from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=2,
    argon2__memory_cost=65536,
)

_BCRYPT_MAX_BYTES = 72


def _truncate_for_bcrypt(plain_password: str) -> str:
    """Truncate to 72 bytes for legacy bcrypt verification only."""
    encoded = plain_password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_BYTES:
        return plain_password
    return encoded[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="replace")


def hash_password(plain_password: str) -> str:
    """Hash a plain password for storage. Uses Argon2 (no 72-byte limit)."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored hash. Supports Argon2 and legacy bcrypt."""
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        plain_password = _truncate_for_bcrypt(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


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
    "pwd_context",
]
