"""Tests and test results API. Submit creates a result and enqueues AI refinement job."""

from fastapi import APIRouter, Depends, Query

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.questions import QUESTIONS_BY_TEST_ID
from app.constants.tests import TESTS, get_test_id
from app.core.dependencies import get_current_active_user, get_db, get_optional_current_user
from app.core.exceptions import conflict, not_found
from app.core.queue import enqueue_refine_test_result
from app.core.redis import cache_get, cache_set, cache_key_test_list, TEST_LIST_CACHE_TTL
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.schemas.test_result import (
    AstrologyBlueprintResponse,
    AstrologyChartNarrativeResponse,
    AstrologyChartResponse,
    EnergySynthesisResponse,
    LifePathNumberResponse,
    NumerologyBlueprintItem,
    NumerologyBlueprintResponse,
    NumerologyResponse,
    QuestionOut,
    SoulCompassResponse,
    SoulUrgeResponse,
    SubmitTestRequest,
    SubmitTestResponse,
    TestListItem,
    TestsListResponse,
    TestResultResponse,
)
from app.services.llm import (
    call_llm_for_astrology_blueprint,
    call_llm_for_astrology_chart_narrative,
    call_llm_for_numerology_blueprint,
)
from app.services.result_calculation.astrology import compute_astrology
from app.services.result_calculation.energy_synthesis import compute_energy_synthesis
from app.services.result_calculation.life_path_number import compute_life_path_number
from app.services.result_calculation.numerology import compute_numerology
from app.services.result_calculation.soul_urge import compute_soul_urge

router = APIRouter()

def _auto_generated_already_taken(user: UserModel, test_id: int) -> bool:
    """True if this test (no separate test—result from existing data) is covered by user's onboarding data (birth, name)."""
    if test_id == 1:
        return (
            user.birth_year is not None
            and user.birth_month is not None
            and user.birth_day is not None
        )
    if test_id == 2:  # Numerology
        return (
            user.birth_year is not None
            and user.birth_month is not None
            and user.birth_day is not None
            and bool((user.name or "").strip())
        )
    return False

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
                TestResult.status.in_(["pending_ai", "completed"]),
            )
        )
        completed_test_ids = {row[0] for row in result.all()}

    tests = []
    for t in catalog:
        tid = t["id"]
        is_completed = tid in completed_test_ids
        is_auto = t.get("auto_generated", False)
        is_premium = t.get("premium", False)
        if (
            is_auto
            and user is not None
            and not is_premium
            and _auto_generated_already_taken(user, tid)
        ):
            already_taken = True
        else:
            already_taken = is_completed
        tests.append(
            TestListItem(
                id=tid,
                slug=t.get("slug") or f"test-{tid}",
                title=t["title"],
                category=t["category"],
                category_id=t["category_id"],
                questions=t["questions"],
                premium=t.get("premium", False),
                auto_generated=is_auto,
                already_taken=already_taken,
            )
        )
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


@router.get("/tests/astrology-chart-narrative", response_model=AstrologyChartNarrativeResponse)
async def get_astrology_chart_narrative(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return AI-generated full narrative for the Astrology Chart result view.
    Requires same birth data as astrology-chart. Used when displaying the chart result (Explore).
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

    existing_q = await db.execute(
        select(TestResult).where(
            TestResult.user_id == user.id,
            TestResult.test_id == 1,
            TestResult.test_title == "Astrology Chart Narrative",
        ).order_by(TestResult.completed_at.desc()).limit(1)
    )
    existing = existing_q.scalar_one_or_none()
    if existing is not None and isinstance(existing.llm_result_json, dict):
        data = existing.llm_result_json
    else:
        el = result.get("element_distribution") or {}
        data = await call_llm_for_astrology_chart_narrative(
            sun_sign=result["sun_sign"],
            moon_sign=result["moon_sign"],
            rising_sign=result["rising_sign"],
            element_distribution={
                "fire": el.get("fire", 0),
                "earth": el.get("earth", 0),
                "air": el.get("air", 0),
                "water": el.get("water", 0),
            },
        )
        if existing is None:
            existing = TestResult(
                user_id=user.id,
                test_id=1,
                test_title="Astrology Chart Narrative",
                category="Cosmic Identity",
                answers=result,
                status="completed",
                score=None,
                personality_type=None,
                insights=None,
                recommendations=None,
                narrative=data.get("narrative", ""),
                extracted_json=result,
                llm_result_json=data,
            )
            db.add(existing)
        else:
            existing.llm_result_json = data
            existing.narrative = data.get("narrative", "")
            existing.extracted_json = result
            existing.status = "completed"
        await db.commit()

    overlaps = [
        {"label": o.get("label", ""), "description": o.get("description", "")}
        for o in data.get("overlaps", [])
    ]
    return AstrologyChartNarrativeResponse(
        title=data.get("title", "Your Astrology Chart"),
        core_traits=data.get("coreTraits", []),
        narrative=data.get("narrative", ""),
        strengths=data.get("strengths", []),
        challenges=data.get("challenges", []),
        avoid_this=data.get("avoidThis", []),
        overlaps=overlaps,
        try_this=data.get("tryThis", []),
        spiritual_insight=data.get("spiritualInsight", ""),
    )


@router.get("/tests/numerology", response_model=NumerologyResponse)
async def get_numerology(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current user's numerology (life path, soul urge, birthday number, expression).
    Computed from stored birth date and name. Persists values to user profile.
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        raise not_found("Birth date incomplete; need year, month, and day.")
    name_for_numerology = (user.full_name or user.name or "").strip()
    if not name_for_numerology:
        raise not_found("Name or full name is required for Soul Urge and Expression.")

    result = compute_numerology(
        birth_year=user.birth_year,
        birth_month=user.birth_month,
        birth_day=user.birth_day,
        name=name_for_numerology,
    )
    if result is None:
        raise not_found("Could not compute numerology for this data.")

    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(
            life_path_number=result["life_path"],
            soul_urge_number=result["soul_urge"],
            expression_number=result["expression_number"],
        )
    )
    await db.commit()

    return NumerologyResponse(
        life_path=result["life_path"],
        soul_urge=result["soul_urge"],
        birthday_number=result["birthday_number"],
        expression_number=result["expression_number"],
    )


@router.get("/tests/onboarding/astrology-blueprint", response_model=AstrologyBlueprintResponse)
async def get_onboarding_astrology_blueprint(
    user: UserModel = Depends(get_current_active_user),
):
    """
    AI-generated copy for the onboarding astrology blueprint screen.
    Requires full birth data (date + place). Used only in onboarding flow.
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

    el = result.get("element_distribution") or {}
    data = await call_llm_for_astrology_blueprint(
        sun_sign=result["sun_sign"],
        moon_sign=result["moon_sign"],
        rising_sign=result["rising_sign"],
        element_distribution={
            "fire": el.get("fire", 0),
            "earth": el.get("earth", 0),
            "air": el.get("air", 0),
            "water": el.get("water", 0),
        },
    )
    return AstrologyBlueprintResponse(
        sun_description=data.get("sunDescription", ""),
        moon_description=data.get("moonDescription", ""),
        rising_description=data.get("risingDescription", ""),
        cosmic_traits_summary=data.get("cosmicTraitsSummary", ""),
    )


@router.get("/tests/onboarding/numerology-blueprint", response_model=NumerologyBlueprintResponse)
async def get_onboarding_numerology_blueprint(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI-generated copy for the onboarding numerology blueprint screen.
    Requires birth date and name. Persists life path, soul urge, birthday, expression to user. Used only in onboarding flow.
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        raise not_found("Birth date incomplete.")
    name_for_numerology = (user.full_name or user.name or "").strip()
    if not name_for_numerology:
        raise not_found("Name or full name is required for Soul Urge and Expression.")

    result = compute_numerology(
        birth_year=user.birth_year,
        birth_month=user.birth_month,
        birth_day=user.birth_day,
        name=name_for_numerology,
    )
    if result is None:
        raise not_found("Could not compute numerology for this data.")

    data = await call_llm_for_numerology_blueprint(
        life_path=result["life_path"],
        soul_urge=result["soul_urge"],
        birthday_number=result["birthday_number"],
        expression_number=result["expression_number"],
    )

    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(
            life_path_number=result["life_path"],
            soul_urge_number=result["soul_urge"],
            expression_number=result["expression_number"],
        )
    )
    await db.commit()

    return NumerologyBlueprintResponse(
        items=[NumerologyBlueprintItem(**i) for i in data.get("items", [])],
    )


@router.get("/tests/life-path-number", response_model=LifePathNumberResponse)
async def get_life_path_number(
    user: UserModel = Depends(get_current_active_user),
):
    """
    Life Path Number from date of birth: sum digits, reduce to 1–9 or keep 11/22/33.
    Returns lifePath, traits[], strengths[], challenges[].
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        raise not_found("Birth date incomplete; need year, month, and day.")
    result = compute_life_path_number(
        birth_year=user.birth_year,
        birth_month=user.birth_month,
        birth_day=user.birth_day,
    )
    if result is None:
        raise not_found("Could not compute Life Path Number for this date.")
    return LifePathNumberResponse(
        lifePath=result["lifePath"],
        traits=result["traits"],
        strengths=result["strengths"],
        challenges=result["challenges"],
    )


@router.get("/tests/soul-urge", response_model=SoulUrgeResponse)
async def get_soul_urge(
    user: UserModel = Depends(get_current_active_user),
):
    """
        Soul Urge / Heart's Desire from vowels in first name (Pythagorean).
        Uses first name only (e.g. 'John' from full_name or name). Returns soulUrge, traits[], strengths[], challenges[].
    """
    full_name = (user.full_name or user.name or "").strip()
    if not full_name:
        raise not_found("Full name or name is required for Soul Urge calculation.")
    result = compute_soul_urge(full_name=full_name)
    if result is None:
        raise not_found("Could not compute Soul Urge for this name.")
    return SoulUrgeResponse(
        soulUrge=result["soulUrge"],
        traits=result["traits"],
        strengths=result["strengths"],
        challenges=result["challenges"],
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
    """Create a test result and enqueue exactly one AI refinement job. Poll GET /tests/results/{result_id} for completion."""
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


LIFE_PATH_TEST_ID = 19

@router.post("/tests/ensure-onboarding-life-path")
async def ensure_onboarding_life_path(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """After onboarding, ensure Life Path (19) result exists. Creates a result and enqueues worker if user has DOB and no existing result."""
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        return {"queued": False, "reason": "missing_dob"}
    existing = await db.execute(
        select(TestResult.id).where(
            TestResult.user_id == user.id,
            TestResult.test_id == LIFE_PATH_TEST_ID,
        ).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return {"queued": False, "already_exists": True}
    test_item = next((t for t in TESTS if t["id"] == LIFE_PATH_TEST_ID), None)
    if not test_item:
        return {"queued": False, "reason": "test_not_found"}
    row = TestResult(
        user_id=user.id,
        test_id=LIFE_PATH_TEST_ID,
        test_title=test_item["title"],
        category=test_item["category"],
        answers=[],
        status="pending_ai",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    enqueued = await enqueue_refine_test_result(row.id)
    return {"queued": enqueued, "result_id": row.id}


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
    db: AsyncSession = Depends(get_db),
):
    """Return questions for a test. Accepts numeric id or slug. Returns 409 if user has already taken this test."""
    test_id = get_test_id(id_or_slug)
    if test_id is None:
        raise not_found("Test not found")
    existing = await db.execute(
        select(TestResult.id).where(
            TestResult.user_id == user.id,
            TestResult.test_id == test_id,
            TestResult.status.in_(["pending_ai", "completed"]),
        ).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("You have already taken this test.")
    return QUESTIONS_BY_TEST_ID.get(test_id, [])
