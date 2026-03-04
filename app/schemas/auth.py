import calendar
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


# 24-hour time HH:mm, hours 0-23, minutes 0-59
BIRTH_TIME_PATTERN = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_time: str | None = Field(None, max_length=50)
    birth_place: str | None = Field(None, max_length=255)
    birth_place_lat: float | None = None
    birth_place_lng: float | None = None
    birth_place_timezone: str | None = Field(None, max_length=64)

    @field_validator("name")
    @classmethod
    def name_first_and_last(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name is required.")
        parts = trimmed.split()
        if len(parts) < 2:
            raise ValueError("Please enter first and last name (e.g. John Doe).")
        for part in parts:
            if len(part) < 2:
                raise ValueError("Each name part must be at least 2 characters.")
        return trimmed

    @field_validator("birth_time")
    @classmethod
    def birth_time_24h(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        s = v.strip()
        if not BIRTH_TIME_PATTERN.match(s):
            raise ValueError("Time must be in 24-hour format (e.g. 14:30). Hours 0-23, minutes 0-59.")
        return s

    @field_validator("birth_day", mode="after")
    @classmethod
    def birth_day_valid_for_month(cls, v: int, info) -> int:
        year = info.data.get("birth_year")
        month = info.data.get("birth_month")
        if year is None or month is None:
            return v
        _, last = calendar.monthrange(year, month)
        if v > last:
            raise ValueError(f"Day must be between 1 and {last} for the selected month.")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ResetPasswordResponse(BaseModel):
    message: str
