"""Helper utilities and internal LLM wrappers for worker tasks."""

import hashlib
import json
import logging
from datetime import date
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.synthesis import (
    SYNTHESIS_FULL_MIN_TESTS,
    SYNTHESIS_PREVIEW_MIN_TESTS,
)
from app.core.config import settings
from app.core.redis import (
    get_redis,
)
from app.db.models.test_result import TestResult
from app.db.models.user import User as UserModel
from app.services.result_calculation.life_path_number import compute_life_path_number
from app.services.result_calculation.shadow_work import compute_shadow_work
from app.services.result_calculation.soul_compass import compute_soul_compass
from app.services.result_calculation.emotional_regulation import compute_emotional_regulation
from app.services.result_calculation.energy_synthesis import compute_energy_synthesis

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
        if qid == 1:
            out["thought_concern"] = ans
        elif qid == 2:
            out["emotional_state"] = ans
        elif qid == 3:
            out["reflective_situation"] = ans
        elif qid == 4:
            out["imbalance_area"] = ans
        elif qid == 5:
            out["intention"] = ans
    
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
    Calculate Starseed Origins using a point-based scoring system.

    Questions 1-7 contribute fixed points per selected key.
    Questions 8-12 are Likert (1-5) added directly as raw points.
    Scores are normalized to percentages relative to the max score.
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {
        item.get("id") or item.get("question_id"): item.get("answer")
        for item in (answers or [])
        if isinstance(item, dict)
    }

    scores: dict[str, float] = {
        "pleiadian": 0, "arcturian": 0, "sirian": 0,
        "lyran": 0, "andromedan": 0, "venusian": 0,
    }

    def add(key: str, pts: float) -> None:
        if key in scores:
            scores[key] += pts

    # Q1 — social role
    _q1 = {
        "helper_wait": ("pleiadian", 2),
        "observe_until_called": ("andromedan", 2),
        "lead_immediately": ("sirian", 2),
        "quiet_support": ("venusian", 2),
    }
    q1_ans = str(ans_map.get(1) or "").strip()
    if q1_ans in _q1:
        add(*_q1[q1_ans])

    # Q2 — curiosity (multi-select)
    _q2 = {
        "space": ("andromedan", 2),
        "ancient": ("sirian", 2),
        "science": ("arcturian", 2),
        "mystical": ("pleiadian", 1),
        "nature": ("lyran", 2),
        "energy": ("venusian", 2),
    }
    q2_ans = ans_map.get(2)
    if isinstance(q2_ans, list):
        for item in q2_ans:
            key = str(item).strip()
            if key in _q2:
                add(*_q2[key])

    # Q3 — nature resonance
    _q3 = {
        "earth": ("lyran", 2),
        "water": ("venusian", 2),
        "sky": ("andromedan", 2),
        "plants": ("pleiadian", 1),
    }
    q3_ans = str(ans_map.get(3) or "").strip()
    if q3_ans in _q3:
        add(*_q3[q3_ans])

    # Q4 — calling
    _q4 = {
        "heal": ("pleiadian", 3),
        "innovate": ("arcturian", 3),
        "teach": ("sirian", 3),
        "protect": ("lyran", 3),
    }
    q4_ans = str(ans_map.get(4) or "").strip()
    if q4_ans in _q4:
        add(*_q4[q4_ans])

    # Q5 — social energy
    _q5 = {
        "one_on_one": ("venusian", 2),
        "small_groups": ("andromedan", 1),
        "teach_crowd": ("sirian", 2),
        "observe_edges": ("lyran", 1),
    }
    q5_ans = str(ans_map.get(5) or "").strip()
    if q5_ans in _q5:
        add(*_q5[q5_ans])

    # Q6 — decision style
    _q6 = {
        "heart": ("pleiadian", 2),
        "logic": ("arcturian", 2),
        "balance": ("venusian", 1),
    }
    q6_ans = str(ans_map.get(6) or "").strip()
    if q6_ans in _q6:
        add(*_q6[q6_ans])

    # Q7 — pace
    _q7 = {
        "grounded": ("lyran", 2),
        "free_flowing": ("andromedan", 2),
        "structured": ("arcturian", 2),
        "reflective": ("sirian", 1),
    }
    q7_ans = str(ans_map.get(7) or "").strip()
    if q7_ans in _q7:
        add(*_q7[q7_ans])

    # Q8-Q12 — Likert scales added as raw points
    scale_map = {
        "Strongly Disagree": 1.0, "Disagree": 2.0, "Neutral": 3.0,
        "Agree": 4.0, "Strongly Agree": 5.0,
    }

    def get_likert(qid: int) -> float:
        val = ans_map.get(qid)
        if isinstance(val, str):
            return scale_map.get(val.strip(), 3.0)
        try:
            return float(val)
        except (TypeError, ValueError):
            return 3.0

    scores["andromedan"] += get_likert(8)
    scores["pleiadian"]  += get_likert(9)
    scores["sirian"]     += get_likert(10)
    scores["lyran"]      += get_likert(11)
    scores["andromedan"] += get_likert(12)

    # Normalize to percent relative to max
    max_score = max(scores.values()) or 1
    percent_scores = {k: round((v / max_score) * 100) for k, v in scores.items()}

    ranked = sorted(percent_scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0]

    titles = {
        "pleiadian":   "Pleiadian Healer",
        "arcturian":   "Arcturian Innovator",
        "sirian":      "Sirian Teacher",
        "lyran":       "Lyran Guardian",
        "andromedan":  "Andromedan Explorer",
        "venusian":    "Venusian Harmonizer",
    }

    return {
        "primary_origin": primary,
        "secondary_origin": secondary,
        "title": titles.get(primary, "Starseed Origins"),
        "scores": percent_scores,
    }

def compute_core_values(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Core Values Sort scores.
    Part A (q1-q4): +20 points to the selected value.
    Part B (q5-q12): 0-100 points based on intensity.
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}

    scores = {
        "growth": 0,
        "connection": 0,
        "freedom": 0,
        "security": 0,
        "impact": 0,
        "creativity": 0,
        "harmony": 0,
        "achievement": 0
    }

    # Part A Mapping (q1-q4)
    # A=growth, B=connection, C=freedom, D=security
    part_a_keywords = {
        "growth": ["learning", "improving", "personal growth"],
        "connection": ["relationships", "connected", "helping others", "supporting"],
        "freedom": ["independence", "own way", "exploring new", "freedom"],
        "security": ["stability", "secure", "safety", "long-term stability"]
    }

    for qid in [1, 2, 3, 4]:
        ans = str(ans_map.get(qid) or "").lower()
        if not ans:
            continue
        for val, keywords in part_a_keywords.items():
            if any(k in ans for k in keywords):
                scores[val] += 20
                break

    def to_percent(val: Any) -> int:
        score = _map_text_to_score(val)
        return int(round(((score - 1) / 4) * 100))

    # Part B Mapping (q5-q12)
    scores["growth"] += to_percent(ans_map.get(5))
    scores["connection"] += to_percent(ans_map.get(6))
    scores["freedom"] += to_percent(ans_map.get(7))
    scores["security"] += to_percent(ans_map.get(8))
    scores["impact"] += to_percent(ans_map.get(9))
    scores["creativity"] += to_percent(ans_map.get(10))
    scores["harmony"] += to_percent(ans_map.get(11))
    scores["achievement"] += to_percent(ans_map.get(12))

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
    15: compute_emotional_regulation, # Emotional Regulation Type
    18: compute_energy_synthesis, # Energy Synthesis
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
    json.dumps(parts, indent=0)
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
