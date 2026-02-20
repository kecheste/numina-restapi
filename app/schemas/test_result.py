"""Schemas for test results and test catalog (frontend-aligned)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TestWithStatusItem(BaseModel):
    """Single test with user-relevant status (from GET /tests)."""

    id: int
    title: str
    category: str
    category_id: str
    questions: int
    auto_generated: bool
    premium: bool
    already_taken: bool


class TestsListResponse(BaseModel):
    """GET /tests response: catalog + user context."""

    user_is_premium: bool
    tests: list[TestWithStatusItem]


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


class QuestionResponse(BaseModel):
    """Single question for GET /tests/{test_id}/questions."""

    id: int
    prompt: str
    answer_type: str  # text | date | time | single_choice | multiple_choice | slider
    options: list[str] | None = None
    slider_min: int = 0
    slider_max: int = 100
    required: bool = True
