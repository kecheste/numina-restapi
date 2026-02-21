from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import conflict, unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User as UserModel
from app.schemas.auth import LoginRequest, RegisterRequest, Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate with email and password; return a JWT access token."""
    result = await db.execute(
        select(UserModel).where(UserModel.email == body.email.lower())
    )
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise unauthorized("Incorrect email or password")

    if not verify_password(body.password, user.hashed_password):
        raise unauthorized("Incorrect email or password")

    if not user.is_active:
        raise unauthorized("Account is disabled")

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
    )
    return Token(access_token=access_token)


@router.post("/register", response_model=Token)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Create a new user and return a JWT access token."""
    result = await db.execute(
        select(UserModel).where(UserModel.email == body.email.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise conflict("Email already registered")

    hashed = hash_password(body.password)
    # Build from request body so birth_place_lat, birth_place_lng, birth_place_timezone are never missed
    register_data = body.model_dump(exclude={"password", "email"})
    user = UserModel(
        email=body.email.lower(),
        hashed_password=hashed,
        is_active=True,
        role="user",
        is_premium=False,
        subscription_status="free",
        **register_data,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
    )
    return Token(access_token=access_token)
