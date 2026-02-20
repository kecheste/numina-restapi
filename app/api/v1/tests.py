"""Tests and test results API. Submit creates a result and enqueues AI refinement job."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.tests import TESTS
from app.constants.test_questions import TEST_QUESTIONS
from app.core.dependencies import get_current_active_user, get_db
from app.core.exceptions import forbidden, not_found
from app.core.queue import enqueue_refine_test_result
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.schemas.test_result import (
    QuestionResponse,
    SubmitTestRequest,
    SubmitTestResponse,
    TestResultResponse,
    TestWithStatusItem,
    TestsListResponse,
)

router = APIRouter()

@router.get("/tests", response_model=TestsListResponse)
async def list_tests(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return test catalog with user context: user_is_premium, and per-test premium + already_taken. Auth required."""
    r = await db.execute(
        select(TestResult.test_id).where(TestResult.user_id == user.id)
    )
    taken_test_ids = {row[0] for row in r.fetchall()}

    tests_with_status = [
        TestWithStatusItem(
            id=t["id"],
            title=t["title"],
            category=t["category"],
            category_id=t["category_id"],
            questions=t["questions"],
            auto_generated=t["auto_generated"],
            premium=t["premium"],
            already_taken=(t["id"] in taken_test_ids),
        )
        for t in TESTS
    ]

    return TestsListResponse(
        user_is_premium=user.is_premium,
        tests=tests_with_status,
    )


def _get_test_by_id(test_id: int) -> dict | None:
    for t in TESTS:
        if t["id"] == test_id:
            return t
    return None


@router.get("/tests/{test_id}/questions", response_model=list[QuestionResponse])
async def get_test_questions(
    test_id: int,
    user: UserModel = Depends(get_current_active_user),
):
    """Return questions for a test. Empty list if test has no questions (e.g. auto-generated only)."""
    if _get_test_by_id(test_id) is None:
        raise not_found("Test not found")
    raw = TEST_QUESTIONS.get(test_id, [])
    out = []
    for q in raw:
        out.append(
            QuestionResponse(
                id=q["id"],
                prompt=q["prompt"],
                answer_type=q["answer_type"],
                options=q.get("options"),
                slider_min=q.get("slider_min", 0),
                slider_max=q.get("slider_max", 100),
                required=q.get("required", True),
            )
        )
    return out


@router.post("/tests/submit", response_model=SubmitTestResponse)
async def submit_test(
    body: SubmitTestRequest,
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test result and enqueue AI refinement. Poll GET /tests/results/{result_id} for completion."""
    test_def = _get_test_by_id(body.test_id)
    if test_def and test_def.get("premium") and not user.is_premium:
        raise forbidden("This test requires a premium subscription.")
    row = TestResult(
        user_id=user.id,
        test_id=body.test_id,
        test_title=body.test_title,
        category=body.category,
        answers=body.answers,
        status="pending_ai",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    enqueued = await enqueue_refine_test_result(row.id)
    if not enqueued:
        pass  # still saved; worker or manual process can pick up later

    return SubmitTestResponse(result_id=row.id, status="pending_ai")


@router.get("/tests/results", response_model=list[TestResultResponse])
async def list_results(
    test_id: int | None = Query(None),
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's test results, optionally filtered by test_id. Sorted by completed_at desc."""
    q = select(TestResult).where(TestResult.user_id == user.id)
    if test_id is not None:
        q = q.where(TestResult.test_id == test_id)
    q = q.order_by(TestResult.completed_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()
    return list(rows)


@router.get("/tests/results/{result_id}", response_model=TestResultResponse)
async def get_result(
    result_id: int,
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single result by id (must belong to current user). For polling after submit."""
    r = await db.execute(
        select(TestResult).where(
            TestResult.id == result_id,
            TestResult.user_id == user.id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Test result not found")
    return row
