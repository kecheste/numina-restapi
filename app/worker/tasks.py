"""Arq tasks: AI refinement and other async jobs."""

import hashlib
import json
import logging
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import (
    AI_RESULT_CACHE_TTL,
    cache_get,
    cache_key_ai_result,
    cache_set,
    get_redis,
    init_redis,
)
from app.db.models.test_result import TestResult
from app.db.session import AsyncSessionLocal
from app.services.result_calculation.mbti import compute_mbti

logger = logging.getLogger(__name__)

# Rate limit key: user:ai_requests:YYYY-MM-DD
AI_RATE_LIMIT_PREFIX = "user:ai_requests:"


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
            row.status = "completed"
            await session.commit()
            return

        # 3) Computed result for tests with deterministic type (e.g. MBTI)
        computed_type: str | None = None
        if test_id == 7:  # MBTI Type
            computed_type = compute_mbti(row.answers)
            if computed_type:
                row.personality_type = computed_type

        # 4) Call AI (token-limited) for score, insights, recommendations
        out = await _call_openai_for_insights(
            row.test_title,
            row.category,
            row.answers,
        )
        row.score = out["score"]
        if computed_type is None:
            row.personality_type = out["personality_type"]
        # else keep row.personality_type as computed (MBTI)
        row.insights = out["insights"]
        row.recommendations = out["recommendations"]
        row.status = "completed"

        # Cache: store computed type if we have one so cache reflects it
        if computed_type:
            out = {**out, "personality_type": computed_type}
        await cache_set(cache_key, out, ttl_seconds=AI_RESULT_CACHE_TTL)
        await session.commit()
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
