"""Tests and test results API. Submit creates a result and enqueues AI refinement job."""

from fastapi import APIRouter, Depends, Query

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal

from app.constants.questions import QUESTIONS_BY_TEST_ID
from app.constants.tests import TESTS, get_test_id
from app.core.dependencies import get_current_active_user, get_db, get_optional_current_user
from app.core.exceptions import conflict, not_found
from app.core.queue import (
    enqueue_refine_test_result,
    enqueue_astrology_blueprint,
    enqueue_numerology_blueprint,
)
from app.core.redis import cache_get, cache_set, cache_key_test_list, TEST_LIST_CACHE_TTL
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.schemas.test_result import (
    AstrologyBlueprintResponse,
    AstrologyChartNarrativeOverlap,
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
    if test_id == 4:  # Human Design
        return (
            user.birth_year is not None
            and user.birth_month is not None
            and user.birth_day is not None
            and user.birth_place_lat is not None
            and user.birth_place_lng is not None
            and user.birth_place_timezone is not None
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
        sun_description=user.sun_description,
        moon_description=user.moon_description,
        rising_description=user.rising_description,
        cosmic_traits_summary=user.cosmic_traits_summary,
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
    if existing is None:
        existing = TestResult(
            user_id=user.id,
            test_id=1,
            test_title="Astrology Chart Narrative",
            category="Cosmic Identity",
            answers=result,
            status="pending_ai",
            extracted_json=result,
        )
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        await enqueue_refine_test_result(existing.id)

    if existing.status == "pending_ai":
        return AstrologyChartNarrativeResponse(
            status="pending_ai",
            result_id=existing.id,
        )

    data = existing.llm_result_json or {}
    overlaps = [
        AstrologyChartNarrativeOverlap(label=o.get("label", ""), description=o.get("description", ""))
        for o in data.get("overlaps", [])
    ]
    return AstrologyChartNarrativeResponse(
        status="completed",
        result_id=existing.id,
        title=data.get("title", "Your Astrology Chart"),
        core_traits=data.get("coreTraits", []),
        narrative=data.get("narrative", ""),
        strengths=data.get("strengths", []),
        challenges=data.get("challenges", []),
        avoid_this=data.get("avoidThis", []),
        overlaps=overlaps,
        try_this=data.get("tryThis", []),
        spiritual_insight=data.get("spiritualInsight", ""),
        sun_description=user.sun_description,
        moon_description=user.moon_description,
        rising_description=user.rising_description,
        cosmic_traits_summary=user.cosmic_traits_summary,
    )



@router.get("/tests/numerology", response_model=NumerologyResponse)
async def get_numerology(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current user's numerology (life path, soul urge, birth day, expression).
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

    blueprint = user.numerology_blueprint or []
    lp_desc = next((i["description"] for i in blueprint if i["title"] == "Life Path"), None)
    su_desc = next((i["description"] for i in blueprint if i["title"] == "Soul Urge"), None)
    bd_desc = next((i["description"] for i in blueprint if i["title"] == "Birthday Number"), None)
    ex_desc = next((i["description"] for i in blueprint if i["title"] == "Expression"), None)

    if not blueprint:
        from app.core.queue import enqueue_numerology_blueprint
        await enqueue_numerology_blueprint(user.id)

    return NumerologyResponse(
        life_path=result["life_path"],
        soul_urge=result["soul_urge"],
        birth_day=result["birth_day"],
        expression_number=result["expression_number"],
        life_path_description=lp_desc,
        soul_urge_description=su_desc,
        birth_day_description=bd_desc,
        expression_description=ex_desc,
        items=[NumerologyBlueprintItem(**i) for i in blueprint] if blueprint else None
    )


@router.get("/tests/onboarding/astrology-blueprint", response_model=AstrologyBlueprintResponse)
async def get_onboarding_astrology_blueprint(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns astrology blueprint teaser data from user profile.
    Trigger worker if not present.
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
        or user.birth_place_lat is None
        or user.birth_place_lng is None
        or user.birth_place_timezone is None
    ):
        raise not_found("Birth data incomplete.")

    if not user.sun_description:
        await enqueue_astrology_blueprint(user.id)
        return AstrologyBlueprintResponse(
            status="pending_ai",
        )

    data = user.astrology_blueprint or {}
    overlaps = [
        AstrologyChartNarrativeOverlap(label=o.get("label", ""), description=o.get("description", ""))
        for o in data.get("overlaps", [])
    ] if isinstance(data.get("overlaps"), list) else []

    return AstrologyBlueprintResponse(
        status="completed",
        sun_description=user.sun_description,
        moon_description=user.moon_description,
        rising_description=user.rising_description,
        cosmic_traits_summary=user.cosmic_traits_summary,
        strengths=data.get("strengths", []),
        challenges=data.get("challenges", []),
        avoid_this=data.get("avoidThis", []),
        overlaps=overlaps,
        try_this=data.get("tryThis", []),
        spiritual_insight=data.get("spiritualInsight", ""),
    )


@router.get("/tests/onboarding/numerology-blueprint", response_model=NumerologyBlueprintResponse)
async def get_onboarding_numerology_blueprint(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns numerology blueprint teaser data (items) from user profile.
    Trigger worker if not present.
    """
    if (
        user.birth_year is None
        or user.birth_month is None
        or user.birth_day is None
    ):
        raise not_found("Birth date incomplete.")

    name_for_numerology = (user.full_name or user.name or "").strip()
    if not name_for_numerology:
        raise not_found("Name is required.")

    if not user.numerology_blueprint:
        await enqueue_numerology_blueprint(user.id)
        return NumerologyBlueprintResponse(
            status="pending_ai",
        )

    return NumerologyBlueprintResponse(
        status="completed",
        items=[NumerologyBlueprintItem(**i) for i in user.numerology_blueprint],
    )


@router.post("/tests/onboarding/finish")
async def post_onboarding_finish(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete the onboarding process:
    1) Verify required tests (7, 13)
    2) Auto-generate Life Path Number (19) result
    3) Finalize user profile and trigger synthesis
    """
    # 1. Verification (Optional but good pattern)
    # 2. Auto-generate Life Path (19)
    if (
        user.birth_year is not None
        and user.birth_month is not None
        and user.birth_day is not None
    ):
        lp_data = compute_life_path_number(
            birth_year=user.birth_year,
            birth_month=user.birth_month,
            birth_day=user.birth_day,
        )
        if lp_data:
            # Check if exists
            exists_q = await db.execute(
                select(TestResult).where(
                    TestResult.user_id == user.id,
                    TestResult.test_id == 19
                ).limit(1)
            )
            if exists_q.scalar_one_or_none() is None:
                lp_res = TestResult(
                    user_id=user.id,
                    test_id=19,
                    test_title="Life Path Number",
                    category="Soul Path & Karma",
                    answers=lp_data,
                    status="pending_ai",
                    extracted_json=lp_data,
                )
                db.add(lp_res)
                await db.commit()
                await db.refresh(lp_res)
                await enqueue_refine_test_result(lp_res.id)

        # 2b. Auto-generate Human Design (4)
        if (
            user.birth_place_lat is not None
            and user.birth_place_lng is not None
            and user.birth_place_timezone is not None
        ):
            hd_exists_q = await db.execute(
                select(TestResult).where(
                    TestResult.user_id == user.id,
                    TestResult.test_id == 4
                ).limit(1)
            )
            if hd_exists_q.scalar_one_or_none() is None:
                hd_res = TestResult(
                    user_id=user.id,
                    test_id=4,
                    test_title="Human Design",
                    category="Cosmic Identity",
                    answers={},
                    status="pending_ai",
                    extracted_json={},
                )
                db.add(hd_res)
                await db.commit()
                await db.refresh(hd_res)
                await enqueue_refine_test_result(hd_res.id)

    # 3. Trigger Synthesis (Ensure it's ready for first home view)
    async with AsyncSessionLocal() as session:
        from app.worker.helpers import generate_synthesis_for_user
        await generate_synthesis_for_user(session, user.id)

    return {"message": "Onboarding completed"}


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
    """Create a test result and enqueue exactly one AI refinement job. Returns existing result if already exists.
    Guarantees at most one result row per user per test_id."""

    existing_q = await db.execute(
        select(TestResult).where(
            TestResult.user_id == user.id,
            TestResult.test_id == body.test_id,
            TestResult.status.in_(["pending_ai", "completed"]),
        ).order_by(TestResult.completed_at.desc()).limit(1)
    )
    existing = existing_q.scalar_one_or_none()
    if existing is not None:
        return SubmitTestResponse(result_id=existing.id, status=existing.status)

    answers_data = [item.model_dump() for item in body.answers]

    extracted_json_data = None
    if body.test_id == 1:
        if (
            user.birth_year is not None
            and user.birth_month is not None
            and user.birth_day is not None
            and user.birth_place_lat is not None
            and user.birth_place_lng is not None
            and user.birth_place_timezone is not None
        ):
            astro_result = compute_astrology(
                birth_year=user.birth_year,
                birth_month=user.birth_month,
                birth_day=user.birth_day,
                birth_time=user.birth_time,
                birth_place_lat=user.birth_place_lat,
                birth_place_lng=user.birth_place_lng,
                birth_place_timezone=user.birth_place_timezone,
            )
            if astro_result:
                extracted_json_data = {
                    **astro_result,
                    "sun_description": user.sun_description or "",
                    "moon_description": user.moon_description or "",
                    "rising_description": user.rising_description or "",
                    "cosmic_traits_summary": user.cosmic_traits_summary or "",
                }
                answers_data = extracted_json_data

    row = TestResult(
        user_id=user.id,
        test_id=body.test_id,
        test_title=body.test_title,
        category=body.category,
        answers=answers_data,
        status="pending_ai",
        extracted_json=extracted_json_data,
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
