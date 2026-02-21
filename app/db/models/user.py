from sqlalchemy import Float, String, DateTime, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_place_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_place_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_place_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_status: Mapped[str] = mapped_column(
        String(50), default="free", nullable=False
    )
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
