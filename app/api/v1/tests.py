"""Tests and test results API. Submit creates a result and enqueues AI refinement job."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.tests import TESTS
from app.core.dependencies import get_current_active_user, get_db
from app.core.exceptions import not_found
from app.core.queue import enqueue_refine_test_result
from app.core.redis import cache_get, cache_set, cache_key_test_list, TEST_LIST_CACHE_TTL
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.schemas.test_result import (
    SubmitTestRequest,
    SubmitTestResponse,
    TestResultResponse,
)

router = APIRouter()


@router.get("/tests")
async def list_tests():
    """Return test catalog (cached). Frontend uses this with completed state from GET /tests/results."""
    cached = await cache_get(cache_key_test_list())
    if cached is not None:
        return cached
    await cache_set(cache_key_test_list(), TESTS, ttl_seconds=TEST_LIST_CACHE_TTL)
    return TESTS


@router.post("/tests/submit", response_model=SubmitTestResponse)
async def submit_test(
    body: SubmitTestRequest,
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test result and enqueue AI refinement. Poll GET /tests/results/{result_id} for completion."""
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
