from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Profile as returned to frontend (aligned with frontend UserProfile)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None
    full_name: str | None = None  # optional; used for Soul Urge / Heart's Desire
    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    birth_time: str | None
    birth_place: str | None
    birth_place_lat: float | None
    birth_place_lng: float | None
    birth_place_timezone: str | None
    is_premium: bool
    subscription_status: str
    is_active: bool
    role: str
    life_path_number: int | None = None
    soul_urge_number: int | None = None
    expression_number: int | None = None
    mbti_type: str | None = None
    mbti_descriptor: str | None = None
    strongest_chakra: str | None = None
    # Astrology Blueprint
    sun_sign: str | None = None
    sun_description: str | None = None
    moon_sign: str | None = None
    moon_description: str | None = None
    rising_sign: str | None = None
    rising_description: str | None = None
    cosmic_traits_summary: str | None = None
    astrology_blueprint: dict | None = None
    # Numerology Blueprint
    numerology_blueprint: list | None = None

    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Allowed fields for PATCH /users/me."""

    name: str | None = None
    full_name: str | None = Field(None, max_length=255)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    birth_month: int | None = Field(None, ge=1, le=12)
    birth_day: int | None = Field(None, ge=1, le=31)
    birth_time: str | None = Field(None, max_length=50)
    birth_place: str | None = Field(None, max_length=255)
    birth_place_lat: float | None = None
    birth_place_lng: float | None = None
    birth_place_timezone: str | None = Field(None, max_length=64)
