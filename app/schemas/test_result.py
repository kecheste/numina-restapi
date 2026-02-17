"""Schemas for test results (frontend-aligned)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TestResultResponse(BaseModel):
    """Single test result as returned to frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_id: int
    test_title: str
    category: str
    completed_at: datetime
    answers: dict[str, Any]
    status: str
    score: float | None
    personality_type: str | None
    insights: list[str] | None
    recommendations: list[str] | None


class SubmitTestRequest(BaseModel):
    """Body for POST /tests/submit."""

    test_id: int
    test_title: str
    category: str
    answers: dict[str, Any]


class SubmitTestResponse(BaseModel):
    """Response after submitting a test: poll GET /tests/results/{id} for completion."""

    result_id: int
    status: str = "pending_ai"
    message: str = "Result is being refined. Poll GET /tests/results/{result_id} for the completed result."
