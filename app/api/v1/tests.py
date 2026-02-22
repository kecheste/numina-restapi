"""Tests and test results API. Submit creates a result and enqueues AI refinement job."""

from fastapi import APIRouter, Depends, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.questions import QUESTIONS_BY_TEST_ID
from app.constants.tests import TESTS, get_test_id
from app.core.dependencies import get_current_active_user, get_db, get_optional_current_user
from app.core.exceptions import not_found
from app.core.queue import enqueue_refine_test_result
from app.core.redis import cache_get, cache_set, cache_key_test_list, TEST_LIST_CACHE_TTL
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.schemas.test_result import (
    AstrologyChartResponse,
    EnergySynthesisResponse,
    NumerologyResponse,
    QuestionOut,
    SubmitTestRequest,
    SubmitTestResponse,
    TestListItem,
    TestsListResponse,
    TestResultResponse,
)
from app.services.result_calculation.astrology import compute_astrology
from app.services.result_calculation.energy_synthesis import compute_energy_synthesis
from app.services.result_calculation.numerology import compute_numerology

router = APIRouter()


@router.get("/tests", response_model=TestsListResponse)
async def list_tests(
    user: UserModel | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return test catalog with user_is_premium and already_taken. Catalog is cached."""
    cached = await cache_get(cache_key_test_list())
    if cached is not None:
        catalog = cached
    else:
        await cache_set(cache_key_test_list(), TESTS, ttl_seconds=TEST_LIST_CACHE_TTL)
        catalog = TESTS

    user_is_premium = user.is_premium if user else False
    completed_test_ids: set[int] = set()
    if user is not None:
        result = await db.execute(
            select(TestResult.test_id).where(
                TestResult.user_id == user.id,
                TestResult.status == "completed",
            )
        )
        completed_test_ids = {row[0] for row in result.all()}

    tests = [
        TestListItem(
            id=t["id"],
            slug=t.get("slug") or f"test-{t['id']}",
            title=t["title"],
            category=t["category"],
            category_id=t["category_id"],
            questions=t["questions"],
            premium=t.get("premium", False),
            auto_generated=t.get("auto_generated", False),
            already_taken=t["id"] in completed_test_ids,
        )
        for t in catalog
    ]
    return TestsListResponse(user_is_premium=user_is_premium, tests=tests)


@router.get("/tests/astrology-chart", response_model=AstrologyChartResponse)
async def get_astrology_chart(
    user: UserModel = Depends(get_current_active_user),
):
    """
    Return the current user's astrology chart (sun, moon, rising, elements).
    Computed from stored birth date, time, and place (lat/lng/timezone).
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
        or user.birth_place_lat is None
        or user.birth_place_lng is None
        or user.birth_place_timezone is None
    ):
        raise not_found("Birth data incomplete; need date and place (with coordinates and timezone).")

    result = compute_astrology(
        birth_year=user.birth_year,
        birth_month=user.birth_month,
        birth_day=user.birth_day,
        birth_time=user.birth_time,
        birth_place_lat=user.birth_place_lat,
        birth_place_lng=user.birth_place_lng,
        birth_place_timezone=user.birth_place_timezone,
    )
    if result is None:
        raise not_found("Could not compute astrology chart for this birth data.")

    return AstrologyChartResponse(
        sun_sign=result["sun_sign"],
        moon_sign=result["moon_sign"],
        rising_sign=result["rising_sign"],
        element_distribution=result["element_distribution"],
    )


@router.get("/tests/numerology", response_model=NumerologyResponse)
async def get_numerology(
    user: UserModel = Depends(get_current_active_user),
):
    """
    Return the current user's numerology (life path, soul urge).
    Computed from stored birth date and name.
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        raise not_found("Birth date incomplete; need year, month, and day.")
    if not (user.name or "").strip():
        raise not_found("Name is required for Soul Urge calculation.")

    result = compute_numerology(
        birth_year=user.birth_year,
        birth_month=user.birth_month,
        birth_day=user.birth_day,
        name=user.name or "",
    )
    if result is None:
        raise not_found("Could not compute numerology for this data.")

    return NumerologyResponse(
        life_path=result["life_path"],
        soul_urge=result["soul_urge"],
    )


@router.get("/tests/energy-synthesis", response_model=EnergySynthesisResponse)
async def get_energy_synthesis(
    primary_axis: str = Query(..., description="Primary axis, e.g. 'mind' for mindVal=100"),
    heart_status: str = Query(..., description="Heart chakra status, e.g. 'Balanced' for heartVal=100"),
):
    """
    Return Energy Synthesis (fusion type and average) from primary axis and heart status.
    Call with values from Cognitive Style and Chakra Assessment (or other sources).
    """
    result = compute_energy_synthesis(
        primary_axis=primary_axis,
        heart_status=heart_status,
    )
    return EnergySynthesisResponse(
        fusion=result["fusion"],
        avg=result["avg"],
    )


@router.post("/tests/submit", response_model=SubmitTestResponse)
async def submit_test(
    body: SubmitTestRequest,
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test result and enqueue AI refinement. Poll GET /tests/results/{result_id} for completion."""
    answers_data = [item.model_dump() for item in body.answers]
    row = TestResult(
        user_id=user.id,
        test_id=body.test_id,
        test_title=body.test_title,
        category=body.category,
        answers=answers_data,
        status="pending_ai",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    enqueued = await enqueue_refine_test_result(row.id)
    if not enqueued:
        pass

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


@router.get("/tests/{id_or_slug}/questions", response_model=list[QuestionOut])
async def list_questions(
    id_or_slug: str,
    user: UserModel = Depends(get_current_active_user),
):
    """Return questions for a test. Accepts numeric id or slug (e.g. chakra-assessment-scan). Returns [] for tests with no questions defined."""
    test_id = get_test_id(id_or_slug)
    if test_id is None:
        raise not_found("Test not found")
    return QUESTIONS_BY_TEST_ID.get(test_id, [])
