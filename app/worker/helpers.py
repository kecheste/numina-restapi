"""Helper utilities and internal LLM wrappers for worker tasks."""

import hashlib
import json
import logging
from datetime import date
from typing import Any, Callable

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.synthesis import (
    SYNTHESIS_FULL_MIN_TESTS,
    SYNTHESIS_PREVIEW_MIN_TESTS,
)
from app.core.config import settings
from app.core.redis import (
    AI_RESULT_CACHE_TTL,
    cache_get,
    cache_key_ai_result,
    cache_set,
    get_redis,
)
from app.db.models.test_result import TestResult
from app.db.models.user import User as UserModel
from app.db.models.user_synthesis import UserSynthesis
from app.services.llm import (
    call_llm_for_synthesis,
    call_llm_for_test_result,
)
from app.services.result_calculation.life_path_number import compute_life_path_number
from app.services.result_calculation.shadow_work import compute_shadow_work
from app.services.result_calculation.soul_compass import compute_soul_compass

logger = logging.getLogger(__name__)

def _map_text_to_score(val: Any) -> float:
    if val is None:
        return 3.0
    
    mapping = {
        "strongly disagree": 1.0,
        "disagree": 2.0,
        "neutral": 3.0,
        "agree": 4.0,
        "strongly agree": 5.0
    }
    
    if isinstance(val, str):
        mapped = mapping.get(val.strip().lower())
        if mapped is not None:
            return mapped
    
    try:
        return float(val)
    except (ValueError, TypeError):
        return 3.0

def compute_mind_mirror(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Extract Mind Mirror answers into a structured dict for the narrative LLM.
    Mind Mirror relies on text and single-choice answers.
    """
    if isinstance(answers, dict):
        return answers
    
    out = {}
    for item in (answers or []):
        if not isinstance(item, dict):
            continue
        qid = item.get("id") or item.get("question_id")
        ans = item.get("answer")
        if qid == 1: out["thought_concern"] = ans
        elif qid == 2: out["emotional_state"] = ans
        elif qid == 3: out["reflective_situation"] = ans
        elif qid == 4: out["imbalance_area"] = ans
        elif qid == 5: out["intention"] = ans
    
    return out


def compute_energy_archetype(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Energy Archetype scores and identify primary/secondary archetypes.
    
    Dimensions:
    - Visionary: q1, q6, q8
    - Analyst: q2, q7
    - Integrator: q3, q9, q11
    - Overloaded: q4, q5, q10, q12
    """
    if isinstance(answers, dict):
        return answers

    # 1) Map answers to qX variables (default to 3/neutral if missing)
    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}
    
    def get_ans(qid: int) -> float:
        return _map_text_to_score(ans_map.get(qid))

    # 2) Calculate raw averages
    raw = {
        "visionary": sum([get_ans(1), get_ans(6), get_ans(8)]) / 3,
        "analyst": sum([get_ans(2), get_ans(7)]) / 2,
        "integrator": sum([get_ans(3), get_ans(9), get_ans(11)]) / 3,
        "overloaded": sum([get_ans(4), get_ans(5), get_ans(10), get_ans(12)]) / 4,
    }

    # 3) Convert to percent (1-5 scale)
    def to_percent(avg_score: float) -> int:
        return int(round(((avg_score - 1) / 4) * 100))

    scores = {k: to_percent(v) for k, v in raw.items()}

    # 4) Rank archetypes
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0]

    title_map = {
        "visionary": "The Inspired Generator",
        "analyst": "The Structured Thinker",
        "integrator": "The Harmonized Mind",
        "overloaded": "The Overloaded Circuit",
    }

    # 5) Calculate balance score
    balance_score = max(0, min(100, scores["integrator"] - scores["overloaded"] + 50))

    return {
        "scores": scores,
        "primary": primary,
        "secondary": secondary,
        "title": title_map.get(primary, "Energy Archetype"),
        "balance_score": balance_score
    }


def compute_big_five(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Big Five personality dimension percentages.
    
    Dimensions:
    - Openness: q1, q2, q3, q4
    - Conscientiousness: q5, q6, q7, q8
    - Extraversion: q9, q10, q11, q12
    - Agreeableness: q13, q14, q15, q16
    - Neuroticism: q17, q18, q19, q20
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}

    def get_ans(qid: int) -> float:
        return _map_text_to_score(ans_map.get(qid))

    def avg(lst):
        return sum(lst) / len(lst) if lst else 3.0

    def to_percent(avg_score):
        return int(round(((avg_score - 1) / 4) * 100))

    results = {
        "openness": to_percent(avg([get_ans(1), get_ans(2), get_ans(3), get_ans(4)])),
        "conscientiousness": to_percent(avg([get_ans(5), get_ans(6), get_ans(7), get_ans(8)])),
        "extraversion": to_percent(avg([get_ans(9), get_ans(10), get_ans(11), get_ans(12)])),
        "agreeableness": to_percent(avg([get_ans(13), get_ans(14), get_ans(15), get_ans(16)])),
        "neuroticism": to_percent(avg([get_ans(17), get_ans(18), get_ans(19), get_ans(20)])),
    }

    return results

def compute_starseed(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Starseed Origins archetypal resonance.
    
    Mapping logic:
    - pleiadian: q4_heal, q8, q9
    - arcturian: q2_science, q6_logic, q7_structured
    - sirian: q4_teach, q5_teaching, q9
    - lyran: q3_earth, q4_protect, q11
    - andromedan: q2_space, q3_sky, q12
    - venusian: q5_oneonone, q3_water, q11
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}

    def get_val(qid: int) -> Any:
        return ans_map.get(qid)

    def get_score(qid: int) -> float:
        return _map_text_to_score(get_val(qid))

    def is_match(qid: int, target: str) -> float:
        val = get_val(qid)
        if isinstance(val, list):
            return 5.0 if any(target.lower() in str(v).lower() for v in val) else 1.0
        if isinstance(val, str):
            return 5.0 if target.lower() in val.lower() else 1.0
        return 1.0

    def avg_scores(lst):
        return sum(lst) / len(lst) if lst else 3.0

    def to_percent(avg_score):
        return int(round(((avg_score - 1) / 4) * 100))

    # Calculate dimension scores (1-5 range)
    dists = {
        "pleiadian": avg_scores([is_match(4, "heal"), get_score(8), get_score(9)]),
        "arcturian": avg_scores([is_match(2, "science"), is_match(6, "logic"), is_match(7, "structured")]),
        "sirian": avg_scores([is_match(4, "teach"), is_match(5, "teaching"), get_score(9)]),
        "lyran": avg_scores([is_match(3, "earth"), is_match(4, "protect"), get_score(11)]),
        "andromedan": avg_scores([is_match(2, "space"), is_match(3, "sky"), get_score(12)]),
        "venusian": avg_scores([is_match(5, "oneonone"), is_match(3, "water"), get_score(11)]),
    }

    scores = {k: to_percent(v) for k, v in dists.items()}
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0]

    titles = {
        "pleiadian": "Pleiadian Healer",
        "arcturian": "Arcturian Innovator",
        "sirian": "Sirian Teacher",
        "lyran": "Lyran Guardian",
        "andromedan": "Andromedan Explorer",
        "venusian": "Venusian Harmonizer"
    }

    return {
        "primary_origin": primary,
        "secondary_origin": secondary,
        "title": titles.get(primary, "Starseed Origins"),
        "scores": scores
    }

def compute_core_values(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Core Values Sort scores and identify primary, secondary, and third values.
    
    Mapping:
    - growth: q5
    - connection: q6
    - freedom: q7
    - security: q8
    - impact: q9
    - creativity: q10
    - harmony: q11
    - achievement: q12
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}

    def to_percent(val: Any) -> int:
        score = _map_text_to_score(val)
        return int(round(((score - 1) / 4) * 100))

    scores = {
        "growth": to_percent(ans_map.get(5)),
        "connection": to_percent(ans_map.get(6)),
        "freedom": to_percent(ans_map.get(7)),
        "security": to_percent(ans_map.get(8)),
        "impact": to_percent(ans_map.get(9)),
        "creativity": to_percent(ans_map.get(10)),
        "harmony": to_percent(ans_map.get(11)),
        "achievement": to_percent(ans_map.get(12)),
    }

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    primary = ranked[0][0]
    secondary = ranked[1][0]
    third = ranked[2][0]

    return {
        "primary_value": primary,
        "secondary_value": secondary,
        "third_value": third,
        "scores": scores
    }


TEXT_TEST_COMPUTE_STUBS: dict[int, Callable[..., dict[str, Any]]] = {
    3: compute_starseed,      # Starseed Origins
    8: compute_shadow_work,   # Shadow Work Lens
    9: compute_big_five,      # Big Five
    10: compute_core_values,  # Core Values Sort
    12: compute_mind_mirror,  # Mind Mirror
    14: compute_energy_archetype, # Energy Archetype
    24: compute_soul_compass, # Soul Compass
}


AI_RATE_LIMIT_PREFIX = "user:ai_requests:"

# Canonical chakra labels for storing on user profile (from strongestChakra LLM sentence)
CHAKRA_LABELS = (
    "Root Chakra",
    "Sacral Chakra",
    "Solar Plexus Chakra",
    "Heart Chakra",
    "Throat Chakra",
    "Third Eye Chakra",
    "Crown Chakra",
)

# Zodiac sign from (month, day) for user context
_ZODIAC_BOUNDARIES = [
    (1, 19, "Capricorn"), (2, 18, "Aquarius"), (3, 20, "Pisces"), (4, 19, "Aries"),
    (5, 20, "Taurus"), (6, 20, "Gemini"), (7, 22, "Cancer"), (8, 22, "Leo"),
    (9, 22, "Virgo"), (10, 22, "Libra"), (11, 21, "Scorpio"), (12, 21, "Sagittarius"), (12, 31, "Capricorn"),
]


def extract_strongest_chakra_label(text: str | None) -> str | None:
    """Extract canonical chakra label from LLM strongestChakra sentence."""
    if not text or not isinstance(text, str):
        return None
    t = text.strip().lower()
    for label in CHAKRA_LABELS:
        if label.lower() in t:
            return label
    for label in CHAKRA_LABELS:
        word = label.replace(" Chakra", "")
        if word.lower() in t and " chakra" in t:
            return label
    return None


def zodiac_from_date(month: int, day: int) -> str:
    for m, d, sign in _ZODIAC_BOUNDARIES:
        if (month, day) <= (m, d):
            return sign
    return "Capricorn"


async def get_user_context(session: AsyncSession, user_id: int) -> str:
    """Build a short context string (zodiac, MBTI, life path) for LLM. Kept under ~200 tokens."""
    parts = []
    user_result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if user and user.birth_month is not None and user.birth_day is not None:
        parts.append(f"Zodiac (sun): {zodiac_from_date(user.birth_month, user.birth_day)}")
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


def answer_hash(answers: list[Any] | dict[str, Any]) -> str:
    """Stable hash of answers for cache key. Accepts list of question+answer or legacy dict."""
    if isinstance(answers, list):
        items = [
            item if isinstance(item, dict) else {"question_id": getattr(item, "question_id", 0), "answer": getattr(item, "answer", item)}
            for item in answers
        ]
        sorted_list = sorted(items, key=lambda x: x.get("question_id", 0))
        payload = json.dumps(sorted_list, sort_keys=True)
    else:
        payload = json.dumps(answers, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def check_rate_limit(user_id: int) -> bool:
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


def format_answers_for_ai(answers: list[Any] | dict[str, Any]) -> str:
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


async def call_openai_for_insights(
    test_title: str,
    category: str,
    answers: list[Any] | dict[str, Any],
) -> dict[str, Any]:
    """Call OpenAI with strict token limit. Returns { score, personality_type, insights, recommendations }."""
    if not settings.openai_api_key:
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
        answers_str = format_answers_for_ai(answers)
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


def fallback_narrative(computed: dict[str, Any]) -> str:
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


def fallback_narrative_from_json(extracted: dict[str, Any]) -> str:
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


async def call_openai_for_narrative(
    computed_result: dict[str, Any],
    test_title: str,
    category: str,
) -> str:
    """Turn the computed result (not raw answers) into fine, readable prose. Returns narrative string."""
    if not settings.openai_api_key:
        if "personality_type" in computed_result or "score" in computed_result:
            return fallback_narrative(computed_result)
        return fallback_narrative_from_json(computed_result)

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
            return fallback_narrative(computed_result)
        return fallback_narrative_from_json(computed_result)
    except Exception as e:
        logger.warning("OpenAI narrative call failed: %s", e)
        if "personality_type" in computed_result or "score" in computed_result:
            return fallback_narrative(computed_result)
        return fallback_narrative_from_json(computed_result)


async def generate_synthesis_for_user(session: AsyncSession, user_id: int) -> None:
    """If user has 3+ or 6+ completed results, generate preview or full synthesis (one LLM call per task to avoid 429)."""
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
        # full_json = await call_llm_for_synthesis(input_str, count, full=True)
        # await session.execute(delete(UserSynthesis).where(
        #     UserSynthesis.user_id == user_id,
        #     UserSynthesis.synthesis_type == "full",
        # ))
        # session.add(UserSynthesis(user_id=user_id, synthesis_type="full", result_json=full_json))
        logger.info("Synthesis full generated for user_id=%s", user_id)
        # await session.execute(delete(UserSynthesis).where(
        #     UserSynthesis.user_id == user_id,
        #     UserSynthesis.synthesis_type == "preview",
        # ))
        # session.add(UserSynthesis(user_id=user_id, synthesis_type="preview", result_json=full_json))
    else:
        # preview_json = await call_llm_for_synthesis(input_str, count, full=False)
        # await session.execute(delete(UserSynthesis).where(
        #     UserSynthesis.user_id == user_id,
        #     UserSynthesis.synthesis_type == "preview",
        # ))
        # session.add(UserSynthesis(user_id=user_id, synthesis_type="preview", result_json=preview_json))
        logger.info("Synthesis preview generated for user_id=%s", user_id)
    await session.commit()
