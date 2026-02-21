from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, unauthorized
from app.core.security import InvalidTokenError, decode_access_token
from app.db.models.user import User as UserModel
from app.db.session import AsyncSessionLocal

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """Validate Bearer JWT and return the current user. Raises 401 on invalid token or missing user."""
    if credentials is None:
        raise unauthorized("Not authenticated")
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise unauthorized("Invalid or expired token")

    sub = payload.get("sub")
    if not sub:
        raise unauthorized("Invalid token payload")

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise unauthorized("Invalid token payload")

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise unauthorized("User not found")

    return user


async def get_current_active_user(
    user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Require the current user to be active. Raises 403 if inactive."""
    if not user.is_active:
        raise forbidden("Inactive user")
    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel | None:
    """Return current user if valid Bearer token present, else None. No 401."""
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory: require the current user to have one of the given roles."""

    async def _require_role(
        user: UserModel = Depends(get_current_active_user),
    ) -> UserModel:
        if user.role not in allowed_roles:
            raise forbidden("Insufficient permissions")
        return user

    return _require_role
