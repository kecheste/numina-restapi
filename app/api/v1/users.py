from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db
from app.core.redis import (
    cache_delete,
    cache_get,
    cache_set,
    cache_key_user_profile,
    USER_PROFILE_CACHE_TTL,
)
from app.db.models.user import User as UserModel
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(user: UserModel = Depends(get_current_active_user)) -> UserResponse:
    """Return the currently authenticated user (profile). Cached briefly."""
    cached = await cache_get(cache_key_user_profile(user.id))
    if cached is not None:
        return UserResponse(**cached)
    response = UserResponse.model_validate(user)
    await cache_set(
        cache_key_user_profile(user.id),
        response.model_dump(mode="json"),
        ttl_seconds=USER_PROFILE_CACHE_TTL,
    )
    return response


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user profile (name, birth fields). Invalidates profile cache."""
    if body.name is not None:
        user.name = body.name
    if body.birth_year is not None:
        user.birth_year = body.birth_year
    if body.birth_month is not None:
        user.birth_month = body.birth_month
    if body.birth_day is not None:
        user.birth_day = body.birth_day
    if body.birth_time is not None:
        user.birth_time = body.birth_time
    if body.birth_place is not None:
        user.birth_place = body.birth_place
    await db.commit()
    await db.refresh(user)
    await cache_delete(cache_key_user_profile(user.id))
    return UserResponse.model_validate(user)
