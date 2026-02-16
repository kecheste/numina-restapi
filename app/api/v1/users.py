from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.user import User as UserModel
from app.schemas.user import UserResponse
from app.core.dependencies import get_db

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db)):
    # temporary stub user
    result = await db.execute(select(UserModel).limit(1))
    user = result.scalar_one_or_none()

    if not user:
        raise RuntimeError("No users found")

    return user
