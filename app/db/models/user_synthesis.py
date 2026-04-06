"""User synthesis: preview (3 tests) or full (6+ tests). Stored as JSON for the synthesis screen."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.db.base import Base


class UserSynthesis(Base):
    """One synthesis record per user and type (preview or full). Replaced when recalculated."""

    __tablename__ = "user_synthesis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    synthesis_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "preview" | "full"
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Cached signal payload used to produce result_json.
    # Shape: {"core": [...], "dynamic": [...]}
    # Each element is a module fingerprint dict with a "module_name" key.
    # Stored so new test completions can do an incremental merge instead of a full re-scan.
    input_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
