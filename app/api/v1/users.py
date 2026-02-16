from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.db.models.user import User as UserModel
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(user: UserModel = Depends(get_current_active_user)) -> UserResponse:
    """Return the currently authenticated user."""
    return user
