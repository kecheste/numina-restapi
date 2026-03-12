import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.email import is_email_configured, send_password_reset_email
from app.core.exceptions import bad_request, conflict, unauthorized
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User as UserModel
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
)
from jwt import InvalidTokenError

logger = logging.getLogger(__name__)
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
        raise conflict("A user with that email already exists")

    hashed = hash_password(body.password)
    # Build from request body so birth_place_lat, birth_place_lng, birth_place_timezone are never missed
    register_data = body.model_dump(exclude={"password", "email"})
    user = UserModel(
        email=body.email.lower(),
        hashed_password=hashed,
        is_active=True,
        role="user",
        is_premium=True,
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    """Find account by email; if found, send reset link by email. Never returns the token."""
    result = await db.execute(
        select(UserModel).where(UserModel.email == body.email.lower())
    )
    user = result.scalar_one_or_none()
    message = "If an account exists with that email, you will receive a password reset link."

    if user is not None and is_email_configured() and settings.frontend_url:
        token = create_password_reset_token(user.id)
        base = settings.frontend_url.rstrip("/")
        reset_link = f"{base}/reset-password?token={token}"
        try:
            await send_password_reset_email(user.email, reset_link)
        except Exception as e:
            logger.exception("Failed to send password reset email: %s", e)
            # Still return same message to avoid leaking account existence

    return ForgotPasswordResponse(message=message)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ResetPasswordResponse:
    """Reset password using a valid token from forgot-password."""
    try:
        payload = decode_password_reset_token(body.token)
    except InvalidTokenError:
        raise bad_request("Invalid or expired reset link. Please request a new one.")

    user_id = int(payload["sub"])
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise bad_request("Invalid or expired reset link. Please request a new one.")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    return ResetPasswordResponse(
        message="Your password has been reset. You can now log in."
    )
