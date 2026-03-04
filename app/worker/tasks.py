"""Arq tasks: AI refinement and other async jobs."""

import hashlib
import json
import logging
from datetime import date
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import (
    AI_RESULT_CACHE_TTL,
    cache_delete,
    cache_get,
    cache_key_ai_result,
    cache_key_user_profile,
    cache_set,
    get_redis,
    init_redis,
)
from sqlalchemy import delete, func, update

from app.constants.synthesis import (
    SYNTHESIS_FULL_MIN_TESTS,
    SYNTHESIS_PREVIEW_MIN_TESTS,
)
from app.db.models.test_result import TestResult
from app.db.models.user import User as UserModel
from app.db.models.user_synthesis import UserSynthesis
from app.db.session import AsyncSessionLocal
from app.services.llm import call_llm_for_synthesis, call_llm_for_test_result
from app.services.result_calculation.mbti import compute_mbti
from app.services.result_calculation.life_path_number import compute_life_path_number
from app.services.result_calculation.shadow_work import compute_shadow_work
from app.services.result_calculation.soul_compass import compute_soul_compass
from app.services.result_calculation.soul_urge import compute_soul_urge

logger = logging.getLogger(__name__)

# Test IDs that use compute stub: raw answers stored, extract to compact JSON, narrative from JSON only
TEXT_TEST_COMPUTE_STUBS: dict[int, Callable[..., dict[str, Any]]] = {
    8: compute_shadow_work,   # Shadow Work Lens
    24: compute_soul_compass, # Soul Compass
}

AI_RATE_LIMIT_PREFIX = "user:ai_requests:"

# Zodiac sign from (month, day) for user context
_ZODIAC_BOUNDARIES = [
    (1, 19, "Capricorn"), (2, 18, "Aquarius"), (3, 20, "Pisces"), (4, 19, "Aries"),
    (5, 20, "Taurus"), (6, 20, "Gemini"), (7, 22, "Cancer"), (8, 22, "Leo"),
    (9, 22, "Virgo"), (10, 22, "Libra"), (11, 21, "Scorpio"), (12, 21, "Sagittarius"), (12, 31, "Capricorn"),
]


def _zodiac_from_date(month: int, day: int) -> str:
    for m, d, sign in _ZODIAC_BOUNDARIES:
        if (month, day) <= (m, d):
            return sign
    return "Capricorn"


async def _get_user_context(session: AsyncSession, user_id: int) -> str:
    """Build a short context string (zodiac, MBTI, life path) for LLM. Kept under ~200 tokens."""
    parts = []
    user_result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if user and user.birth_month is not None and user.birth_day is not None:
        parts.append(f"Zodiac (sun): {_zodiac_from_date(user.birth_month, user.birth_day)}")
    mbti_result = await session.execute(
        select(TestResult.personality_type)
        .where(TestResult.user_id == user_id, TestResult.test_id == 7, TestResult.status == "completed")
        .order_by(TestResult.completed_at.desc())
        .limit(1)
    )
    mbti = mbti_result.scalar_one_or_none()
    if mbti:
        parts.append(f"MBTI: {mbti}")
    if user and user.birth_year is not None and user.birth_month is not None and user.birth_day is not None:
        try:
            lp = compute_life_path_number(
                birth_year=user.birth_year,
                birth_month=user.birth_month,
                birth_day=user.birth_day,
            )
            if lp:
                parts.append(f"Life Path Number: {lp.get('lifePath')}")
        except Exception:
            pass
    return "; ".join(parts) if parts else ""


def _answer_hash(answers: list[Any] | dict[str, Any]) -> str:
    """Stable hash of answers for cache key. Accepts list of question+answer or legacy dict."""
    if isinstance(answers, list):
        # Normalize to list of dicts and sort by question_id for stable hash
        items = [
            item if isinstance(item, dict) else {"question_id": getattr(item, "question_id", 0), "answer": getattr(item, "answer", item)}
            for item in answers
        ]
        sorted_list = sorted(items, key=lambda x: x.get("question_id", 0))
        payload = json.dumps(sorted_list, sort_keys=True)
    else:
        payload = json.dumps(answers, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]

async def _check_rate_limit(user_id: int) -> bool:
    """Return True if user is under daily limit."""
    r = get_redis()
    if r is None:
        return True
    key = f"{AI_RATE_LIMIT_PREFIX}{date.today().isoformat()}:{user_id}"
    try:
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, 86400 * 2)  # 2 days
        return n <= settings.ai_max_requests_per_user_per_day
    except Exception:
        return True

def _format_answers_for_ai(answers: list[Any] | dict[str, Any]) -> str:
    """Format answers for AI prompt: question+answer pairs or JSON."""
    if isinstance(answers, list):
        parts = []
        for item in answers:
            d = item if isinstance(item, dict) else {"prompt": getattr(item, "prompt", ""), "answer": getattr(item, "answer", item)}
            prompt = d.get("prompt", "")
            answer = d.get("answer", "")
            if isinstance(answer, list):
                answer = ", ".join(str(a) for a in answer)
            parts.append(f"Q: {prompt}\nA: {answer}")
        return "\n\n".join(parts)[:2000]
    return json.dumps(answers)[:1500]


async def _call_openai_for_insights(
    test_title: str,
    category: str,
    answers: list[Any] | dict[str, Any],
) -> dict[str, Any]:
    """Call OpenAI with strict token limit. Returns { score, personality_type, insights, recommendations }."""
    if not settings.openai_api_key:
        # Fallback when no API key (dev or optional AI)
        return {
            "score": 8.0,
            "personality_type": "The Seeker",
            "insights": [
                "Your responses reflect a thoughtful approach to self-discovery.",
                "Consider exploring more tests for a fuller picture.",
            ],
            "recommendations": [
                "Revisit your answers periodically as you grow.",
                "Share your results with trusted others for reflection.",
            ],
        }

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        answers_str = _format_answers_for_ai(answers)
        prompt = (
            f"Test: {test_title} (category: {category}).\n\n"
            f"Question and answer pairs:\n{answers_str}\n\n"
            "Respond with ONLY a valid JSON object with keys: score (number 0-10), personality_type (string), insights (array of 2-4 short strings), recommendations (array of 2-4 short strings). No markdown."
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(settings.ai_max_tokens_per_request, 1024),
            temperature=0.3,
        )
        text = response.choices[0].message.content or "{}"
        text = text.strip().removeprefix("```json").removeprefix("```").strip()
        data = json.loads(text)
        return {
            "score": float(data.get("score", 8.0)),
            "personality_type": str(data.get("personality_type", "The Seeker")),
            "insights": list(data.get("insights", [])),
            "recommendations": list(data.get("recommendations", [])),
        }
    except Exception as e:
        logger.warning("OpenAI call failed: %s", e)
        return {
            "score": 8.0,
            "personality_type": "The Seeker",
            "insights": ["Your responses have been recorded. Refinement will be available soon."],
            "recommendations": ["Check back later for personalized insights."],
        }


def _fallback_narrative(computed: dict[str, Any]) -> str:
    """Build a simple narrative from computed result when no LLM is available."""
    pt = computed.get("personality_type") or "Unknown"
    score = computed.get("score")
    insights = computed.get("insights") or []
    recs = computed.get("recommendations") or []
    parts = [f"Your result: {pt}."]
    if score is not None:
        parts.append(f"Score: {score}/10.")
    if insights:
        parts.append("Key insights: " + " ".join(insights[:3]))
    if recs:
        parts.append("Recommendations: " + " ".join(recs[:3]))
    return " ".join(parts)


def _fallback_narrative_from_json(extracted: dict[str, Any]) -> str:
    """Simple narrative from extracted_json when no LLM."""
    parts = []
    for k, v in extracted.items():
        if isinstance(v, list) and v:
            parts.append(f"{k}: " + ", ".join(str(x) for x in v[:3]))
        elif isinstance(v, dict):
            parts.append(f"{k}: " + json.dumps(v)[:80])
        elif v:
            parts.append(f"{k}: {v}")
    return " ".join(parts)[:500] if parts else "Your responses have been recorded."


async def _generate_synthesis_for_user(session: AsyncSession, user_id: int) -> None:
    """If user has 3+ or 6+ completed results, generate preview or full synthesis (one LLM call per task to avoid 429)."""
    from app.core.config import settings
    if not settings.openai_api_key:
        return
    count_result = await session.execute(
        select(func.count(TestResult.id)).where(
            TestResult.user_id == user_id,
            TestResult.status == "completed",
        )
    )
    count = count_result.scalar() or 0
    if count < SYNTHESIS_PREVIEW_MIN_TESTS:
        return
    rows_result = await session.execute(
        select(TestResult)
        .where(
            TestResult.user_id == user_id,
            TestResult.status == "completed",
        )
        .order_by(TestResult.completed_at.asc())
    )
    rows = list(rows_result.scalars().all())
    parts = []
    for r in rows:
        blob = r.llm_result_json or r.extracted_json
        if isinstance(blob, dict):
            parts.append({"test": r.test_title, "data": blob})
        elif blob:
            parts.append({"test": r.test_title, "data": blob})
    input_str = json.dumps(parts, indent=0)
    if count >= SYNTHESIS_FULL_MIN_TESTS:
        full_json = await call_llm_for_synthesis(input_str, count, full=True)
        await session.execute(delete(UserSynthesis).where(
            UserSynthesis.user_id == user_id,
            UserSynthesis.synthesis_type == "full",
        ))
        session.add(UserSynthesis(user_id=user_id, synthesis_type="full", result_json=full_json))
        logger.info("Synthesis full generated for user_id=%s", user_id)
        await session.execute(delete(UserSynthesis).where(
            UserSynthesis.user_id == user_id,
            UserSynthesis.synthesis_type == "preview",
        ))
        session.add(UserSynthesis(user_id=user_id, synthesis_type="preview", result_json=full_json))
    else:
        preview_json = await call_llm_for_synthesis(input_str, count, full=False)
        await session.execute(delete(UserSynthesis).where(
            UserSynthesis.user_id == user_id,
            UserSynthesis.synthesis_type == "preview",
        ))
        session.add(UserSynthesis(user_id=user_id, synthesis_type="preview", result_json=preview_json))
        logger.info("Synthesis preview generated for user_id=%s", user_id)
    await session.commit()


async def _call_openai_for_narrative(
    computed_result: dict[str, Any],
    test_title: str,
    category: str,
) -> str:
    """Turn the computed result (not raw answers) into fine, readable prose. Returns narrative string."""
    if not settings.openai_api_key:
        if "personality_type" in computed_result or "score" in computed_result:
            return _fallback_narrative(computed_result)
        return _fallback_narrative_from_json(computed_result)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        data_str = json.dumps(computed_result, indent=2)
        prompt = (
            f"Test: {test_title} (category: {category}).\n\n"
            "Below is the computed result for this user (compact JSON: types, scores, themes, insights, etc.). "
            "Write a short, warm, and well-crafted narrative paragraph (2–4 sentences) that presents this result "
            "in fine writing suitable for displaying to the user. Do not use bullet points or JSON. "
            "Write only the narrative text, nothing else.\n\n"
            f"Computed result:\n{data_str}"
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(settings.ai_max_tokens_per_request, 512),
            temperature=0.5,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
        if "personality_type" in computed_result or "score" in computed_result:
            return _fallback_narrative(computed_result)
        return _fallback_narrative_from_json(computed_result)
    except Exception as e:
        logger.warning("OpenAI narrative call failed: %s", e)
        if "personality_type" in computed_result or "score" in computed_result:
            return _fallback_narrative(computed_result)
        return _fallback_narrative_from_json(computed_result)


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
        answer_hash = _answer_hash(row.answers)

        # 1) Rate limit
        if not await _check_rate_limit(user_id):
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
        cache_key = cache_key_ai_result(test_id, user_id, answer_hash)
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
                        lp = compute_life_path_number(
                            birth_year=user.birth_year,
                            birth_month=user.birth_month,
                            birth_day=user.birth_day,
                        )
                    su = None
                    full_name = (user.full_name or user.name or "").strip()
                    if full_name:
                        su = compute_soul_urge(full_name=full_name)
                    if lp:
                        extracted["lifePath"] = lp
                    if su:
                        extracted["soulUrge"] = su
            except Exception as e:
                logger.warning("Numerology compute failed for user_id=%s: %s", user_id, e)
            user_ctx = await _get_user_context(session, user_id)
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
                await _generate_synthesis_for_user(syn_session, user_id)
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
                            extracted["zodiac"] = _zodiac_from_date(user.birth_month, user.birth_day)
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
                            _zodiac_from_date(user.birth_month, user.birth_day)
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
            user_ctx = await _get_user_context(session, user_id)
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
                await _generate_synthesis_for_user(syn_session, user_id)
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

            user_ctx = await _get_user_context(session, user_id)
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
                await _generate_synthesis_for_user(syn_session, user_id)
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
            user_ctx = await _get_user_context(session, user_id)
            row.extracted_json = extracted
            row.score = 8.0
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
                await _generate_synthesis_for_user(syn_session, user_id)
            logger.info("Refined result_id=%s (stub test)", result_id)
            return

        # 6) Computed result for tests with deterministic type (e.g. MBTI)
        computed_type: str | None = None
        if test_id == 7:  # MBTI Type
            computed_type = compute_mbti(row.answers)
            if computed_type:
                row.personality_type = computed_type

        # 7) Light extraction for standard tests (score, type, insights, recs)
        out = await _call_openai_for_insights(
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
        user_ctx = await _get_user_context(session, user_id)
        llm_result = await call_llm_for_test_result(
            computed_for_llm,
            row.test_title,
            row.category,
            user_context=user_ctx,
        )
        row.llm_result_json = llm_result
        row.personality_type = llm_result.get("title") or row.personality_type
        row.insights = llm_result.get("coreTraits") or out.get("insights", [])
        row.recommendations = llm_result.get("tryThis") or out.get("recommendations", [])
        row.narrative = llm_result.get("summary") or ""

        out["narrative"] = row.narrative
        out["llm_result_json"] = row.llm_result_json
        row.status = "completed"
        await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
        await session.commit()
        async with AsyncSessionLocal() as syn_session:
            await _generate_synthesis_for_user(syn_session, user_id)
        logger.info("Refined result_id=%s", result_id)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: init Redis for cache and rate limiting."""
    try:
        await init_redis()
    except Exception as e:
        logger.warning("Worker Redis init failed (cache/rate limit disabled): %s", e)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown."""
    pass
