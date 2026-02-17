from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Profile as returned to frontend (aligned with frontend UserProfile)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None
    date_of_birth: date | None
    is_premium: bool
    subscription_status: str
    is_active: bool
    role: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Allowed fields for PATCH /users/me."""

    name: str | None = None
    date_of_birth: date | None = None
