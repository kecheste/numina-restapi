from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Profile as returned to frontend (aligned with frontend UserProfile)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None
    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    birth_time: str | None
    birth_place: str | None
    is_premium: bool
    subscription_status: str
    is_active: bool
    role: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Allowed fields for PATCH /users/me."""

    name: str | None = None
    birth_year: int | None = Field(None, ge=1900, le=2100)
    birth_month: int | None = Field(None, ge=1, le=12)
    birth_day: int | None = Field(None, ge=1, le=31)
    birth_time: str | None = Field(None, max_length=50)
    birth_place: str | None = Field(None, max_length=255)
