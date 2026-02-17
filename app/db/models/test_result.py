"""Test attempt and AI-refined result (frontend-aligned)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TestResult(Base):
    """A user's test attempt. After submit, status=pending_ai; worker sets completed."""

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    test_title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="pending_ai", nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    personality_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insights: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
