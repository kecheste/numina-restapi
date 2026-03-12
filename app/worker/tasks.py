"""Arq tasks: AI refinement and other async jobs."""

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import (
    AI_RESULT_CACHE_TTL,
    cache_delete,
    cache_get,
    cache_key_ai_result,
    cache_key_user_profile,
    cache_set,
    init_redis,
)
from app.db.models.test_result import TestResult
from app.db.models.user import User as UserModel
from app.db.session import AsyncSessionLocal

from app.services.result_calculation.astrology import compute_astrology
from app.services.result_calculation.numerology import compute_numerology
from app.services.result_calculation.mbti import compute_mbti_detailed
from app.services.result_calculation.life_path_number import compute_life_path_number
from app.services.result_calculation.soul_urge import compute_soul_urge
from app.services.llm import (
    call_llm_for_astrology_blueprint,
    call_llm_for_astrology_chart_narrative,
    call_llm_for_mbti_narrative,
    call_llm_for_numerology_blueprint,
    call_llm_for_numerology_narrative,
    call_llm_for_test_result,
    call_llm_for_shadow_work,
)

from .helpers import (
    TEXT_TEST_COMPUTE_STUBS,
    answer_hash,
    call_openai_for_insights,
    check_rate_limit,
    extract_strongest_chakra_label,
    generate_synthesis_for_user,
    get_user_context,
    zodiac_from_date,
)

logger = logging.getLogger(__name__)


async def refine_test_result(ctx: dict[str, Any], result_id: int) -> None:
    """Load TestResult by id, (optionally) call AI, cache, save, set status=completed."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            logger.warning("TestResult id=%s not found", result_id)
            return
        if row.status == "completed":
            return

        user_id = row.user_id
        test_id = row.test_id
        answer_hash_val = answer_hash(row.answers)

        # 1) Rate limit
        if not await check_rate_limit(user_id):
            logger.warning("AI rate limit exceeded for user_id=%s", user_id)
            row.status = "completed"
            row.score = 8.0
            row.personality_type = "Rate limit"
            row.insights = ["Daily AI limit reached. Try again tomorrow."]
            row.recommendations = []
            row.narrative = "Your responses have been saved. Daily AI limit reached; check back tomorrow for your full narrative."
            await session.commit()
            return

        # 2) Cache lookup
        cache_key = cache_key_ai_result(test_id, user_id, answer_hash_val)
        cached = await cache_get(cache_key)
        if cached:
            row.score = cached.get("score")
            row.personality_type = cached.get("personality_type")
            row.insights = cached.get("insights", [])
            row.recommendations = cached.get("recommendations", [])
            row.narrative = cached.get("narrative")
            if "extracted_json" in cached:
                row.extracted_json = cached.get("extracted_json")
            if "llm_result_json" in cached:
                row.llm_result_json = cached.get("llm_result_json")
            row.status = "completed"
            await session.commit()
            return

        # 3) Test 2 (Numerology): combined Life Path + Soul Urge from profile → one LLM result
        if test_id == 2:
            extracted = {}
            try:
                user_result = await session.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    lp = None
                    if user.birth_year is not None and user.birth_month is not None and user.birth_day is not None:
                        lp_res = compute_life_path_number(
                            birth_year=user.birth_year,
                            birth_month=user.birth_month,
                            birth_day=user.birth_day,
                        )
                        if lp_res:
                            lp = lp_res.get("lifePath")
                    
                    full_name_clean = (user.full_name or user.name or "").strip()
                    res_num = compute_numerology(
                        birth_year=user.birth_year,
                        birth_month=user.birth_month,
                        birth_day=user.birth_day,
                        name=full_name_clean
                    )
                    
                    if res_num:
                        extracted["lifePath"] = res_num["life_path"]
                        extracted["soulUrge"] = res_num["soul_urge"]
                        extracted["expression_number"] = res_num["expression_number"]
                        extracted["birthday_number"] = res_num["birthday_number"]
            except Exception as e:
                logger.warning("Numerology compute failed for user_id=%s: %s", user_id, e)

            user_ctx = await get_user_context(session, user_id)
            row.extracted_json = extracted
            row.score = 8.0

            lp = extracted.get("lifePath") or 0
            su = extracted.get("soulUrge") or 0
            expr = extracted.get("expression_number") or 0
            bday = extracted.get("birthday_number") or (user.birth_day if user else 0)

            llm_result = await call_llm_for_numerology_narrative(
                life_path=lp,
                soul_urge=su,
                birthday_number=bday,
                expression_number=expr,
                user_context=user_ctx,
            )
            row.llm_result_json = llm_result
            row.personality_type = llm_result.get("title") or row.test_title
            row.insights = llm_result.get("coreTraits") or []
            row.recommendations = llm_result.get("tryThis") or []
            row.narrative = llm_result.get("summary") or ""
            out = {
                "score": row.score,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            row.status = "completed"
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (Numerology)", result_id)
            return

        # 3b) Auto-generated premium: Human Design (4), Energy Synthesis (18) – compute from profile, then one LLM call
        if test_id in (4, 18):
            extracted = {}
            try:
                user_result = await session.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    if test_id == 4:
                        # Human Design: birth data for chart-style narrative (full chart computed elsewhere or by LLM from data)
                        if (
                            user.birth_year is not None
                            and user.birth_month is not None
                            and user.birth_day is not None
                        ):
                            extracted["birthDate"] = f"{user.birth_year}-{user.birth_month:02d}-{user.birth_day:02d}"
                            extracted["zodiac"] = zodiac_from_date(user.birth_month, user.birth_day)
                        if user.birth_time:
                            extracted["birthTime"] = user.birth_time
                        if user.birth_place_lat is not None and user.birth_place_lng is not None:
                            extracted["birthPlace"] = "provided"
                    elif test_id == 18:
                        # Energy Synthesis: aggregate from user context (zodiac, MBTI, life path, etc.)
                        lp = None
                        if (
                            user.birth_year is not None
                            and user.birth_month is not None
                            and user.birth_day is not None
                        ):
                            try:
                                lp = compute_life_path_number(
                                    user.birth_year,
                                    user.birth_month,
                                    user.birth_day,
                                )
                            except Exception:
                                pass
                        if lp:
                            extracted["lifePath"] = lp.get("lifePath")
                        extracted["zodiac"] = (
                            zodiac_from_date(user.birth_month, user.birth_day)
                            if user.birth_month is not None and user.birth_day is not None
                            else None
                        )
            except Exception as e:
                logger.warning(
                    "Auto-generated compute failed for test_id=%s user_id=%s: %s",
                    test_id,
                    user_id,
                    e,
                )
            user_ctx = await get_user_context(session, user_id)
            row.extracted_json = extracted
            row.score = 8.0
            llm_result = await call_llm_for_test_result(
                extracted or {},
                row.test_title,
                row.category,
                user_context=user_ctx,
            )
            row.llm_result_json = llm_result
            row.personality_type = llm_result.get("title") or row.test_title
            row.insights = llm_result.get("coreTraits") or llm_result.get("tryThis") or []
            row.recommendations = llm_result.get("tryThis") or llm_result.get("avoidThis") or []
            row.narrative = llm_result.get("summary") or ""
            out = {
                "score": row.score,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            row.status = "completed"
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (auto-generated %s)", result_id, row.test_title)
            return

        # 4) Deterministic Life Path (19) and Soul Urge (20): compute from profile, then one LLM call
        if test_id in (19, 20):
            extracted: dict[str, Any] = {}
            try:
                user_result = await session.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    if test_id == 19:
                        if (
                            user.birth_year is not None
                            and user.birth_month is not None
                            and user.birth_day is not None
                        ):
                            computed = compute_life_path_number(
                                birth_year=user.birth_year,
                                birth_month=user.birth_month,
                                birth_day=user.birth_day,
                            )
                            if computed:
                                extracted = computed
                    elif test_id == 20:
                        full_name = (user.full_name or user.name or "").strip()
                        if full_name:
                            computed = compute_soul_urge(full_name=full_name)
                            if computed:
                                extracted = computed
            except Exception as e:
                logger.warning(
                    "Deterministic numerology compute failed for test_id=%s user_id=%s: %s",
                    test_id,
                    user_id,
                    e,
                )

            user_ctx = await get_user_context(session, user_id)
            row.extracted_json = extracted
            row.score = 8.0
            llm_result = await call_llm_for_test_result(
                extracted or {},
                row.test_title,
                row.category,
                user_context=user_ctx,
            )
            row.llm_result_json = llm_result
            row.personality_type = llm_result.get("title") or row.test_title
            row.insights = llm_result.get("coreTraits") or llm_result.get("tryThis") or []
            row.recommendations = llm_result.get("tryThis") or llm_result.get("avoidThis") or []
            row.narrative = llm_result.get("summary") or ""
            out = {
                "score": row.score,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            row.status = "completed"
            if test_id == 19:
                lp = extracted.get("lifePath")
                if lp is not None and isinstance(lp, (int, float)):
                    await session.execute(
                        update(UserModel).where(UserModel.id == user_id).values(life_path_number=int(lp))
                    )
                    await cache_delete(cache_key_user_profile(user_id))
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (deterministic numerology)", result_id)
            return

        # 5) Text tests with compute stub: store raw in answers, run stub -> extracted_json, then one LLM call -> llm_result_json
        stub_fn = TEXT_TEST_COMPUTE_STUBS.get(test_id)
        if stub_fn is not None:
            try:
                extracted = stub_fn(row.answers)
            except Exception as e:
                logger.warning("Compute stub failed for test_id=%s: %s", test_id, e)
                extracted = {}
            user_ctx = await get_user_context(session, user_id)
            row.extracted_json = extracted
            row.score = 8.0
            
            if test_id == 8:
                llm_result = await call_llm_for_shadow_work(extracted)
            else:
                llm_result = await call_llm_for_test_result(
                    extracted,
                    row.test_title,
                    row.category,
                    user_context=user_ctx,
                )
            
            row.llm_result_json = llm_result
            row.personality_type = llm_result.get("title") or (
                "Shadow Work Profile" if isinstance(extracted.get("scores"), dict) else "Soul Compass" if "coreDrive" in extracted else "Your Result"
            )
            row.insights = llm_result.get("coreTraits") or llm_result.get("tryThis") or []
            row.recommendations = llm_result.get("tryThis") or llm_result.get("avoidThis") or []
            row.narrative = llm_result.get("summary") or ""
            out = {
                "score": row.score,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            row.status = "completed"
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (stub test)", result_id)
            return

        # 6) MBTI Type (ID 7): fully deterministic scoring, AI only writes narrative
        if test_id == 7:
            mbti_result = compute_mbti_detailed(row.answers)
            mbti_type = mbti_result.get("type") or ""
            dimensions = mbti_result.get("dimensions", {})
            confidence = mbti_result.get("confidence", {})

            row.personality_type = mbti_type
            row.extracted_json = mbti_result  # stores type, dimensions, confidence
            row.score = 10.0

            user_ctx = await get_user_context(session, user_id)
            llm_result = await call_llm_for_mbti_narrative(
                mbti_type=mbti_type,
                confidence=confidence,
                user_context=user_ctx,
            )
            row.llm_result_json = llm_result
            row.insights = llm_result.get("coreTraits") or []
            row.recommendations = llm_result.get("strengths") or []
            row.narrative = llm_result.get("narrative") or ""
            row.status = "completed"

            # Persist mbti_type and descriptor to user profile
            if mbti_type:
                await session.execute(
                    update(UserModel)
                    .where(UserModel.id == user_id)
                    .values(
                        mbti_type=mbti_type,
                        mbti_descriptor=llm_result.get("title") or mbti_type,
                    )
                )
                await cache_delete(cache_key_user_profile(user_id))

            out = {
                "score": row.score,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (MBTI → %s)", result_id, mbti_type)
            return

        computed_type: str | None = None
        
        # 6b) Specialized Astrology Chart Narrative (ID 1)
        if test_id == 1 and row.test_title == "Astrology Chart Narrative":
            # Answers should be the computed astrology dict
            ad = row.answers if isinstance(row.answers, dict) else {}
            el = ad.get("element_distribution") or {}
            llm_result = await call_llm_for_astrology_chart_narrative(
                sun_sign=ad.get("sun_sign", ""),
                moon_sign=ad.get("moon_sign", ""),
                rising_sign=ad.get("rising_sign", ""),
                element_distribution={
                    "fire": el.get("fire", 0),
                    "earth": el.get("earth", 0),
                    "air": el.get("air", 0),
                    "water": el.get("water", 0),
                },
            )
            row.llm_result_json = llm_result
            row.personality_type = llm_result.get("title") or "Your Astrology Chart"
            row.insights = llm_result.get("coreTraits") or []
            row.recommendations = llm_result.get("tryThis") or []
            row.narrative = llm_result.get("narrative") or ""
            row.status = "completed"
            
            out = {
                "score": 8.0,
                "personality_type": row.personality_type,
                "insights": row.insights,
                "recommendations": row.recommendations,
                "narrative": row.narrative,
                "extracted_json": row.extracted_json,
                "llm_result_json": row.llm_result_json,
            }
            await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
            await session.commit()
            async with AsyncSessionLocal() as syn_session:
                await generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (Astrology Chart Narrative)", result_id)
            return

        # 7) Light extraction for standard tests (score, type, insights, recs)
        out = await call_openai_for_insights(
            row.test_title,
            row.category,
            row.answers,
        )
        row.score = out["score"]
        if computed_type is None:
            row.personality_type = out["personality_type"]
        computed_for_llm = {
            "personality_type": out.get("personality_type") or computed_type,
            "score": out.get("score"),
            "insights": out.get("insights", []),
            "recommendations": out.get("recommendations", []),
        }

        # 8) Single LLM call for structured JSON (title, summary, coreTraits, strengths, challenges, spiritualInsight, tryThis, avoidThis)
        user_ctx = await get_user_context(session, user_id)
        llm_result = await call_llm_for_test_result(
            computed_for_llm,
            row.test_title,
            row.category,
            user_context=user_ctx,
            include_chakra_preview=(test_id == 13),
        )
        row.llm_result_json = llm_result
        row.personality_type = llm_result.get("title") or row.personality_type
        row.insights = llm_result.get("coreTraits") or out.get("insights", [])
        row.recommendations = llm_result.get("tryThis") or out.get("recommendations", [])
        row.narrative = llm_result.get("summary") or ""

        out["narrative"] = row.narrative
        out["llm_result_json"] = row.llm_result_json
        row.status = "completed"
        # Save onboarding fields to user profile for My Soul page
        if test_id == 7:
            mbti_type = (computed_type or "").strip().upper() if computed_type and len(computed_type) >= 4 else (row.personality_type or "").strip()[:4].upper() or None
            mbti_descriptor = (llm_result.get("title") or "").strip() or None
            if mbti_type or mbti_descriptor:
                await session.execute(
                    update(UserModel).where(UserModel.id == user_id).values(
                        mbti_type=mbti_type[:20] if mbti_type else None,
                        mbti_descriptor=mbti_descriptor[:100] if mbti_descriptor else None,
                    )
                )
                await cache_delete(cache_key_user_profile(user_id))
        elif test_id == 13:
            chakra_label = extract_strongest_chakra_label(llm_result.get("strongestChakra"))
            if chakra_label:
                await session.execute(
                    update(UserModel).where(UserModel.id == user_id).values(strongest_chakra=chakra_label)
                )
                await cache_delete(cache_key_user_profile(user_id))
        await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
        await session.commit()
        async with AsyncSessionLocal() as syn_session:
            await generate_synthesis_for_user(syn_session, user_id)
        logger.info("Refined result_id=%s", result_id)


async def refine_astrology_blueprint(ctx: dict[str, Any], user_id: int) -> None:
    """Worker task to generate astrology blueprint copy and save to User model."""
    async with AsyncSessionLocal() as session:
        user_q = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            logger.warning("User id=%s not found for astrology blueprint", user_id)
            return

        astrology_data = compute_astrology(
            birth_year=user.birth_year,
            birth_month=user.birth_month,
            birth_day=user.birth_day,
            birth_time=user.birth_time,
            birth_place_lat=user.birth_place_lat,
            birth_place_lng=user.birth_place_lng,
            birth_place_timezone=user.birth_place_timezone,
        )
        if not astrology_data:
            return

        el = astrology_data.get("element_distribution") or {}
        llm_result = await call_llm_for_astrology_blueprint(
            sun_sign=astrology_data["sun_sign"],
            moon_sign=astrology_data["moon_sign"],
            rising_sign=astrology_data["rising_sign"],
            element_distribution={
                "fire": el.get("fire", 0),
                "earth": el.get("earth", 0),
                "air": el.get("air", 0),
                "water": el.get("water", 0),
            },
        )
        
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                sun_sign=astrology_data["sun_sign"],
                sun_description=llm_result.get("sunDescription"),
                moon_sign=astrology_data["moon_sign"],
                moon_description=llm_result.get("moonDescription"),
                rising_sign=astrology_data["rising_sign"],
                rising_description=llm_result.get("risingDescription"),
                cosmic_traits_summary=llm_result.get("cosmicTraitsSummary"),
                astrology_blueprint=llm_result,
            )
        )
        await session.commit()
        await cache_delete(cache_key_user_profile(user_id))
        logger.info("Refined astrology blueprint for user_id=%s (saved to User)", user_id)


async def refine_numerology_blueprint(ctx: dict[str, Any], user_id: int) -> None:
    """Worker task to generate numerology blueprint copy and save to User model."""
    async with AsyncSessionLocal() as session:
        user_q = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            logger.warning("User id=%s not found for numerology blueprint", user_id)
            return

        name_for_numerology = (user.full_name or user.name or "").strip()
        num_data = compute_numerology(
            birth_year=user.birth_year,
            birth_month=user.birth_month,
            birth_day=user.birth_day,
            name=name_for_numerology,
        )
        if not num_data:
            return

        llm_result = await call_llm_for_numerology_blueprint(
            life_path=num_data["life_path"],
            soul_urge=num_data["soul_urge"],
            birthday_number=num_data["birthday_number"],
            expression_number=num_data["expression_number"],
        )
        
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                numerology_blueprint=llm_result.get("items"),
                life_path_number=num_data["life_path"],
                soul_urge_number=num_data["soul_urge"],
                expression_number=num_data["expression_number"],
            )
        )
        await session.commit()
        await cache_delete(cache_key_user_profile(user_id))
        logger.info("Refined numerology blueprint for user_id=%s (saved to User)", user_id)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: init Redis for cache and rate limiting."""
    try:
        await init_redis()
    except Exception as e:
        logger.warning("Worker Redis init failed (cache/rate limit disabled): %s", e)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown."""
    pass
