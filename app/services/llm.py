"""
LLM calls with input cap and strict JSON output. Used for test result and synthesis.
"""

import json
import logging
import re
from collections import Counter
from typing import Any

from app.core.config import settings
from app.core.prompts import (
    ASTROLOGY_BLUEPRINT_JSON_KEYS,
    ASTROLOGY_BLUEPRINT_USER,
    ASTROLOGY_CHART_NARRATIVE_JSON_KEYS,
    ASTROLOGY_CHART_NARRATIVE_SYSTEM,
    ASTROLOGY_CHART_NARRATIVE_USER,
    BLUEPRINT_SYSTEM,
    CHAKRA_ALIGNMENT_APPENDIX,
    CHAKRA_PREVIEW_JSON_KEYS,
    CHAKRA_PREVIEW_USER_APPENDIX,
    NUMEROLOGY_BLUEPRINT_JSON_KEYS,
    NUMEROLOGY_BLUEPRINT_USER,
    NUMEROLOGY_NARRATIVE_JSON_KEYS,
    NUMEROLOGY_NARRATIVE_SYSTEM,
    NUMEROLOGY_NARRATIVE_USER,
    SHADOW_WORK_JSON_KEYS,
    SHADOW_WORK_SYSTEM,
    SHADOW_WORK_USER,
    SYNTHESIS_FULL_JSON_KEYS,
    SYNTHESIS_FULL_USER_TEMPLATE,
    SYNTHESIS_PREVIEW_JSON_KEYS,
    SYNTHESIS_PREVIEW_USER_TEMPLATE,
    SYNTHESIS_SYSTEM,
    TEST_RESULT_JSON_KEYS,
    TEST_RESULT_SYSTEM,
    TEST_RESULT_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

INPUT_MAX_CHARS = getattr(settings, "ai_input_max_chars", 3500)
TEST_RESULT_PROMPT_MAX_CHARS = 8000
OUTPUT_MAX_TOKENS = getattr(settings, "ai_result_output_max_tokens", 1000)


def _cap_input(text: str, max_chars: int | None = None) -> str:
    max_chars = max_chars or INPUT_MAX_CHARS
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n\n[...truncated]"


def _extract_json_from_response(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    for prefix in ("```json", "```"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_case_insensitive_val(o: dict, k: str):
    if k in o: return o[k]
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
    if snake in o: return o[snake]
    def normalize(s: str) -> str:
        return s.lower().replace("_", "").replace(" ", "").replace("-", "")
    
    norm_k = normalize(k)
    for ok in o.keys():
        if normalize(ok) == norm_k:
            return o[ok]
    return None


def _validate_and_filter(obj: dict[str, Any], allowed_keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    list_keys = (
        "insights", "recommendations", "sureThings", "growthAreas", "themes",
        "strengths", "shadowPatterns", "coreTraits", "tryThis", "avoidThis",
    )
    out = {}
    for k in allowed_keys:
        v = get_case_insensitive_val(obj, k)
        if v is None:
            continue
        if k in list_keys:
            out[k] = [str(x) for x in v][:8] if isinstance(v, list) else []
        elif k == "synchronicities":
            if isinstance(v, list):
                out[k] = [
                    {"test": str(s.get("test", s.get("label", ""))), "connection": str(s.get("connection", s.get("description", "")))}
                    for s in v if isinstance(s, dict)
                ][:6]
            else:
                out[k] = []
        else:
            out[k] = str(v) if v is not None else ""
    return out


CHAKRA_IDS = ("root", "sacral", "solarPlexus", "heart", "throat", "thirdEye", "crown")
CHAKRA_NAMES = ("Root Chakra", "Sacral Chakra", "Solar Plexus Chakra", "Heart Chakra", "Throat Chakra", "Third Eye Chakra", "Crown Chakra")


def _validate_chakra_alignment_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize chakra test result: standard keys + statusSummary + chakras (7 items) + synchronicities with label/description."""
    base = _validate_and_filter(obj, TEST_RESULT_JSON_KEYS | frozenset({"strongestChakra", "needsRebalancing", "statusSummary"}))
    base["statusSummary"] = str(obj.get("statusSummary") or base.get("summary") or "").strip() or "Your chakra balance reflects your current energy flow."

    synch = obj.get("synchronicities")
    if isinstance(synch, list) and synch:
        base["synchronicities"] = [
            {"label": str(s.get("label") or s.get("test") or ""), "description": str(s.get("description") or s.get("connection") or "")}
            for s in synch if isinstance(s, dict)
        ][:6]
    elif base.get("synchronicities") and isinstance(base["synchronicities"], list):
        base["synchronicities"] = [
            {"label": str(s.get("test", "")), "description": str(s.get("connection", ""))} if isinstance(s, dict) else {"label": "", "description": str(s)}
            for s in base["synchronicities"][:6]
        ]

    raw_chakras = obj.get("chakras") if isinstance(obj.get("chakras"), list) else []
    by_id: dict[str, dict[str, Any]] = {}
    for c in raw_chakras:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip() or None
        if cid in CHAKRA_IDS:
            by_id[cid] = {
                "id": cid,
                "name": str(c.get("name") or "").strip() or CHAKRA_NAMES[CHAKRA_IDS.index(cid)],
                "status": str(c.get("status") or "Balanced").strip(),
                "description": str(c.get("description") or "").strip() or "Energy flow for this center.",
                "tryItems": str(c.get("tryItems")).strip() if c.get("tryItems") else None,
                "avoidItems": str(c.get("avoidItems")).strip() if c.get("avoidItems") else None,
            }
    out_chakras: list[dict[str, Any]] = []
    for i, cid in enumerate(CHAKRA_IDS):
        if cid in by_id:
            out_chakras.append(by_id[cid])
        else:
            out_chakras.append({
                "id": cid,
                "name": CHAKRA_NAMES[i],
                "status": "Balanced",
                "description": "This energy center is in balance.",
                "tryItems": None,
                "avoidItems": None,
            })
    base["chakras"] = out_chakras
    return base


def _validate_shadow_work_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize Shadow Work Lens result."""
    base = _validate_and_filter(obj, SHADOW_WORK_JSON_KEYS)
    # Ensure extracted_json is present and correctly formatted if the LLM moved things
    if "extracted_json" not in base or not isinstance(base["extracted_json"], dict):
        # Fallback if LLM missed it or put it elsewhere
        base["extracted_json"] = obj.get("extracted_json") or obj.get("scores") or {}
    return base


async def call_llm_for_shadow_work(computed_scores: dict[str, Any]) -> dict[str, Any]:
    """Dedicated LLM call for Shadow Work Lens interpretation."""
    if not settings.openai_api_key:
        return _fallback_shadow_work_json()

    user_content = SHADOW_WORK_USER.format(
        input_json=json.dumps(computed_scores, indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": SHADOW_WORK_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.6,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_shadow_work_result(data)
    except Exception as e:
        logger.warning("LLM shadow work call failed: %s", e)
    return _fallback_shadow_work_json()


def _fallback_shadow_work_json() -> dict[str, Any]:
    return {
        "title": "Your Shadow Pattern",
        "summary": "We are preparing a full psychological interpretation of your shadow results.",
        "shortDescription": "We are preparing a compassionate interpretation of your primary shadow pattern.",
        "shadowPattern": "We are preparing a compassionate interpretation of your primary shadow pattern.",
        "secondaryPattern": "Your secondary tendency interacts with your primary pattern in unique ways.",
        "howItShowsUp": "These patterns often appear during times of stress or emotional exposure.",
        "hiddenStrength": "Within every shadow lies a hidden strength waiting to be integrated.",
        "growthEdge": "Awareness is the first step toward transforming these unconscious habits.",
        "tryThis": [
            "Practice naming feelings without judgment",
            "Notice when you feel the urge to pull back or criticize",
            "Offer yourself the same compassion you would a friend"
        ],
        "avoidThis": [
            "Harsh self-criticism for having these patterns",
            "Ignoring the physical sensations that accompany stress"
        ],
        "extracted_json": {}
    }


async def call_llm_for_test_result(
    computed_input: dict[str, Any] | list[Any],
    test_title: str,
    category: str,
    user_context: str = "",
    include_chakra_preview: bool = False,
) -> dict[str, Any]:
    """
    Single LLM call: input is capped; output is strict JSON with title, summary, coreTraits,
    strengths, challenges, spiritualInsight, tryThis, avoidThis, synchronicities.
    When include_chakra_preview=True, also returns strongestChakra and needsRebalancing.
    """
    if not settings.openai_api_key:
        return _fallback_test_result_json(include_chakra_preview=include_chakra_preview)

    input_str = json.dumps(computed_input, indent=0) if isinstance(computed_input, dict) else json.dumps(computed_input)
    user_context = (user_context or "").strip()
    if user_context:
        user_context = "Known about this user (use to enrich the result, keep brief):\n" + user_context
    else:
        user_context = ""

    input_str = _cap_input(input_str, max_chars=6000)
    user_content = TEST_RESULT_USER_TEMPLATE.format(
        test_title=test_title,
        category=category,
        user_context=user_context,
        input_json=input_str,
    )
    if include_chakra_preview:
        user_content = user_content + CHAKRA_PREVIEW_USER_APPENDIX
        user_content = user_content + CHAKRA_ALIGNMENT_APPENDIX
    if len(user_content) > TEST_RESULT_PROMPT_MAX_CHARS:
        user_content = user_content[: TEST_RESULT_PROMPT_MAX_CHARS - 20] + "\n\n[...truncated]"

    allowed_keys = (TEST_RESULT_JSON_KEYS | CHAKRA_PREVIEW_JSON_KEYS) if include_chakra_preview else TEST_RESULT_JSON_KEYS
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TEST_RESULT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=min(settings.ai_max_tokens_per_request, OUTPUT_MAX_TOKENS if not include_chakra_preview else 1200),
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            if include_chakra_preview:
                return _validate_chakra_alignment_result(data)
            return _validate_and_filter(data, allowed_keys)
    except Exception as e:
        logger.warning("LLM test result call failed: %s", e)
    return _fallback_test_result_json(include_chakra_preview=include_chakra_preview)


def _fallback_test_result_json(include_chakra_preview: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "title": "Your Result",
        "summary": "Your responses have been recorded. Insights are being prepared.",
        "shortDescription": "We are preparing a concise summary of your unique path.",
        "coreTraits": ["Reflective", "Growing"],
        "strengths": ["Self-awareness", "Willingness to explore"],
        "challenges": ["Patience", "Integration"],
        "spiritualInsight": "Every step on the path adds clarity.",
        "tryThis": ["Revisit your answers as you grow.", "Explore more tests for a fuller picture."],
        "avoidThis": ["Rushing to conclusions.", "Comparing yourself to others."],
        "synchronicities": [],
    }
    if include_chakra_preview:
        out["strongestChakra"] = "Your energy flows most freely through your Crown Chakra, indicating heightened intuition or spiritual awareness."
        out["needsRebalancing"] = "You may want to bring attention to your Root Chakra, which governs your sense of stability and grounding."
        out["statusSummary"] = "Your chakra balance reflects your current energy flow. Complete the assessment again for a personalized alignment."
        out["chakras"] = [
            {"id": cid, "name": name, "status": "Balanced", "description": "This energy center is in balance.", "tryItems": None, "avoidItems": None}
            for cid, name in zip(CHAKRA_IDS, CHAKRA_NAMES)
        ]
    return out


async def call_llm_for_synthesis(
    input_json: str,
    completed_count: int,
    full: bool,
) -> dict[str, Any]:
    """
    Single LLM call for synthesis. input_json is capped. full=True uses full template and keys.
    Returns validated dict for preview or full synthesis.
    """
    if not settings.openai_api_key:
        return _fallback_synthesis_json(full)

    input_json = _cap_input(input_json)

    if full:
        user_content = SYNTHESIS_FULL_USER_TEMPLATE.format(
            count=completed_count,
            input_json=input_json,
        )
        allowed_keys = SYNTHESIS_FULL_JSON_KEYS
    else:
        user_content = SYNTHESIS_PREVIEW_USER_TEMPLATE.format(
            count=completed_count,
            input_json=input_json,
        )
        allowed_keys = SYNTHESIS_PREVIEW_JSON_KEYS

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=min(settings.ai_max_tokens_per_request, 800),
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_and_filter(data, allowed_keys)
    except Exception as e:
        logger.warning("LLM synthesis call failed: %s", e)
    return _fallback_synthesis_json(full)


def _fallback_synthesis_json(full: bool) -> dict[str, Any]:
    base = {
        "youAre": "Your synthesis is being prepared from your test results.",
        "sureThings": ["Patterns are emerging from your responses."],
        "identitySummary": "Complete more tests to see your integrated portrait.",
        "growthAreas": ["Self-awareness", "Integration"],
        "nextFocus": "Take a few more tests to unlock your full synthesis.",
    }
    if full:
        base["themes"] = []
        base["strengths"] = []
        base["shadowPatterns"] = []
    return base


SIGN_MODALITY = {
    "Aries": "Cardinal",
    "Cancer": "Cardinal",
    "Libra": "Cardinal",
    "Capricorn": "Cardinal",
    "Taurus": "Fixed",
    "Leo": "Fixed",
    "Scorpio": "Fixed",
    "Aquarius": "Fixed",
    "Gemini": "Mutable",
    "Virgo": "Mutable",
    "Sagittarius": "Mutable",
    "Pisces": "Mutable",
}


def calculate_modality(planet_signs: dict[str, str]) -> dict[str, Any]:
    """
    planet_signs example:
    {
        "sun": "Aries",
        "moon": "Taurus",
        "mercury": "Pisces",
        "venus": "Aries",
        "mars": "Leo"
    }
    """

    modality_count: Counter[str] = Counter()

    for _planet, sign in planet_signs.items():
        modality = SIGN_MODALITY.get(sign)
        if modality:
            modality_count[modality] += 1

    if not modality_count:
        return {"counts": {}, "dominant_modality": ""}

    dominant_modality = max(modality_count, key=modality_count.get)

    return {
        "counts": dict(modality_count),
        "dominant_modality": dominant_modality,
    }


def _dominant_element_from_distribution(element_distribution: dict[str, int]) -> str:
    """Return dominant element as 'Fire' | 'Earth' | 'Air' | 'Water' (capitalized)."""
    if not isinstance(element_distribution, dict):
        return ""
    fire = int(element_distribution.get("fire", 0) or 0)
    earth = int(element_distribution.get("earth", 0) or 0)
    air = int(element_distribution.get("air", 0) or 0)
    water = int(element_distribution.get("water", 0) or 0)
    pairs = [("Fire", fire), ("Earth", earth), ("Air", air), ("Water", water)]
    dominant = max(pairs, key=lambda x: x[1])[0] if any(v > 0 for _, v in pairs) else ""
    return dominant


_SIGN_RULERS = {
    "Aries": ["Mars"],
    "Taurus": ["Venus"],
    "Gemini": ["Mercury"],
    "Cancer": ["Moon"],
    "Leo": ["Sun"],
    "Virgo": ["Mercury"],
    "Libra": ["Venus"],
    "Scorpio": ["Mars", "Pluto"],
    "Sagittarius": ["Jupiter"],
    "Capricorn": ["Saturn"],
    "Aquarius": ["Saturn", "Uranus"],
    "Pisces": ["Jupiter", "Neptune"],
}


def _ruling_planets_for_chart(sun_sign: str, rising_sign: str) -> str:
    """Return comma-separated ruling planet(s) based on sun and rising signs."""
    rulers: list[str] = []
    for sign in (sun_sign, rising_sign):
        for planet in _SIGN_RULERS.get(sign, []):
            if planet not in rulers:
                rulers.append(planet)
    return ", ".join(rulers)


_SIGN_TO_HOUSE = {
    "Aries": "1st",
    "Taurus": "2nd",
    "Gemini": "3rd",
    "Cancer": "4th",
    "Leo": "5th",
    "Virgo": "6th",
    "Libra": "7th",
    "Scorpio": "8th",
    "Sagittarius": "9th",
    "Capricorn": "10th",
    "Aquarius": "11th",
    "Pisces": "12th",
}


def _most_emphasized_house(sun_sign: str) -> str:
    """Approximate most emphasized house using natural house of the sun sign."""
    return _SIGN_TO_HOUSE.get(sun_sign, "")


def _validate_astrology_blueprint(obj: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_astrology_blueprint()
    if not isinstance(obj, dict):
        return fallback
    out: dict[str, Any] = {}

    for k in ASTROLOGY_BLUEPRINT_JSON_KEYS:
        v = get_case_insensitive_val(obj, k)
        if k == "overlaps":
            if isinstance(v, list) and v:
                out[k] = [
                    {"label": str(s.get("label", s.get("title", ""))), "description": str(s.get("description", ""))}
                    for s in v if isinstance(s, dict)
                ][:6]
            else:
                out[k] = []
        elif k in ("strengths", "challenges", "avoidThis", "tryThis"):
            out[k] = [str(x) for x in v][:8] if isinstance(v, list) else []
        else:
            s = str(v).strip() if v is not None and isinstance(v, str) else ""
            out[k] = s if s else fallback.get(k, "")
    return out


def _fallback_astrology_blueprint() -> dict[str, Any]:
    return {
        "sunDescription": "Your sun sign shapes your core personality and life direction.",
        "moonDescription": "Your moon sign reveals how you process emotions and seek comfort.",
        "risingDescription": "Your rising sign reflects how others see you and your outward style.",
        "cosmicTraitsSummary": "🜂 Element: —\n☌ Modality: —\n♇ Ruling Planet: —\n🌠 Most active house: —",
        "strengths": [],
        "challenges": [],
        "avoidThis": [],
        "tryThis": [],
        "overlaps": [],
        "spiritualInsight": "",
    }


async def call_llm_for_astrology_blueprint(
    sun_sign: str,
    moon_sign: str,
    rising_sign: str,
    element_distribution: dict[str, int],
) -> dict[str, Any]:
    """Generate short AI copy for onboarding astrology blueprint screen."""
    if not settings.openai_api_key:
        return _fallback_astrology_blueprint()
    fire = element_distribution.get("fire", 0)
    earth = element_distribution.get("earth", 0)
    air = element_distribution.get("air", 0)
    water = element_distribution.get("water", 0)

    dominant_element = _dominant_element_from_distribution(element_distribution)
    modality_info = calculate_modality(
        {
            "sun": sun_sign,
            "moon": moon_sign,
            "rising": rising_sign,
        }
    )
    dominant_modality = modality_info.get("dominant_modality", "")
    ruling_planets = _ruling_planets_for_chart(sun_sign, rising_sign)
    most_emphasized_house = _most_emphasized_house(sun_sign)

    user_content = ASTROLOGY_BLUEPRINT_USER.format(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        rising_sign=rising_sign,
        fire=fire,
        earth=earth,
        air=air,
        water=water,
        dominant_element=dominant_element,
        modality=dominant_modality,
        ruling_planets=ruling_planets,
        most_emphasized_house=most_emphasized_house,
    )
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BLUEPRINT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1000,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_astrology_blueprint(data)
    except Exception as e:
        logger.warning("LLM astrology blueprint call failed: %s", e)
    return _fallback_astrology_blueprint()

def _validate_astrology_chart_narrative(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize astrology chart narrative response."""
    fallback = _fallback_astrology_chart_narrative()
    if not isinstance(obj, dict):
        return fallback
    out: dict[str, Any] = {}
    for k in ASTROLOGY_CHART_NARRATIVE_JSON_KEYS:
        v = get_case_insensitive_val(obj, k)
        if k == "overlaps":
            if isinstance(v, list) and v:
                out[k] = [
                    {"label": str(s.get("label", s.get("title", ""))), "description": str(s.get("description", ""))}
                    for s in v if isinstance(s, dict)
                ][:6]
            else:
                out[k] = []
        elif k in ("coreTraits", "strengths", "challenges", "avoidThis", "tryThis"):
            out[k] = [str(x) for x in v][:8] if isinstance(v, list) else []
        else:
            s = str(v).strip() if v is not None and isinstance(v, str) else ""
            out[k] = s if s else fallback.get(k, "")
            if k == "narrative" and out[k]:
                pass
    return out


def _fallback_astrology_chart_narrative() -> dict[str, Any]:
    return {
        "title": "Your Astrology Chart",
        "coreTraits": ["Reflective", "Intuitive", "Grounded"],
        "narrative": "Your chart blends your sun, moon, and rising signs with your element distribution. You carry both emotional depth and practical grounding. Use this awareness to make choices that honor your nature. Explore your birth chart in depth to uncover more layers and align with your purpose.",
        "strengths": ["Self-awareness", "Emotional depth"],
        "challenges": ["Integration", "Balance"],
        "avoidThis": ["Ignoring your body's needs", "Overthinking"],
        "overlaps": [],
        "tryThis": ["Journal by the moon", "Spend time in nature"],
        "spiritualInsight": "Your birth chart is a map of your soul's journey—use it as a guide, not a limit.",
    }


async def call_llm_for_astrology_chart_narrative(
    sun_sign: str,
    moon_sign: str,
    rising_sign: str,
    element_distribution: dict[str, int],
) -> dict[str, Any]:
    """Generate full detailed narrative for the Astrology Chart result view. Kept independent of other systems (no MBTI/chakra/life path)."""
    if not settings.openai_api_key:
        return _fallback_astrology_chart_narrative()
    fire = element_distribution.get("fire", 0)
    earth = element_distribution.get("earth", 0)
    air = element_distribution.get("air", 0)
    water = element_distribution.get("water", 0)

    dominant_element = _dominant_element_from_distribution(element_distribution)
    modality_info = calculate_modality(
        {
            "sun": sun_sign,
            "moon": moon_sign,
            "rising": rising_sign,
        }
    )
    dominant_modality = modality_info.get("dominant_modality", "")
    ruling_planets = _ruling_planets_for_chart(sun_sign, rising_sign)
    most_emphasized_house = _most_emphasized_house(sun_sign)

    user_content = ASTROLOGY_CHART_NARRATIVE_USER.format(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        rising_sign=rising_sign,
        fire=fire,
        earth=earth,
        air=air,
        water=water,
        dominant_element=dominant_element,
        modality=dominant_modality,
        ruling_planets=ruling_planets,
        most_emphasized_house=most_emphasized_house,
    )
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ASTROLOGY_CHART_NARRATIVE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1200,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_astrology_chart_narrative(data)
    except Exception as e:
        logger.warning("LLM astrology chart narrative call failed: %s", e)
    return _fallback_astrology_chart_narrative()


def _truncate_numerology_description(text: str, max_len: int = 70) -> str:
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    for end in (".", "!", "?"):
        i = s.find(end)
        if i >= 0:
            s = s[: i + 1].strip()
            break
    if len(s) <= max_len:
        return s
    s = s[: max_len + 1]
    last_space = s.rfind(" ")
    if last_space > max_len // 2:
        s = s[:last_space].rstrip()
    else:
        s = s[:max_len].rstrip()
    return s + "." if not s.endswith((".", "!", "?")) else s


def _validate_numerology_blueprint(
    obj: dict[str, Any],
    life_path: int,
    soul_urge: int,
    birthday_number: int,
    expression_number: int,
) -> dict[str, Any]:
    """Ensure exactly 4 items: Life Path, Soul Urge, Birthday Number, Expression (with correct numbers)."""
    fallback = _fallback_numerology_blueprint(
        life_path, soul_urge, birthday_number, expression_number
    )
    if not isinstance(obj, dict):
        return fallback
    items = obj.get("items")
    if not isinstance(items, list) or len(items) < 4:
        return fallback
    expected = [
        ("Life Path", life_path),
        ("Soul Urge", soul_urge),
        ("Birthday Number", birthday_number),
        ("Expression", expression_number),
    ]
    out_items: list[dict[str, str]] = []
    for idx, (title, num) in enumerate(expected):
        row = None
        for i in items:
            if not isinstance(i, dict):
                continue
            t = (i.get("title") or "").strip()
            n = i.get("number")
            if (t.lower() == title.lower() or str(n) == str(num)) and n is not None and i.get("description"):
                row = {
                    "number": str(n),
                    "title": title,
                    "description": _truncate_numerology_description(str(i.get("description"))),
                }
                break
        if not row:
            row = {
                "number": str(num),
                "title": title,
                "description": fallback["items"][idx]["description"],
            }
        out_items.append(row)
    return {"items": out_items}


def _fallback_numerology_blueprint(
    life_path: int,
    soul_urge: int,
    birthday_number: int,
    expression_number: int,
) -> dict[str, Any]:
    return {
        "items": [
            {"number": str(life_path), "title": "Life Path", "description": "Your life path reflects your core purpose and lessons."},
            {"number": str(soul_urge), "title": "Soul Urge", "description": "Your soul urge reveals what your heart truly desires."},
            {"number": str(birthday_number), "title": "Birthday Number", "description": "Your birthday number adds a personal layer to your cosmic profile."},
            {"number": str(expression_number), "title": "Expression", "description": "Your expression number reflects how you show up in the world."},
        ],
    }


async def call_llm_for_numerology_blueprint(
    life_path: int,
    soul_urge: int,
    birthday_number: int,
    expression_number: int,
) -> dict[str, Any]:
    """Generate short AI copy for onboarding numerology blueprint screen."""
    if not settings.openai_api_key:
        return _fallback_numerology_blueprint(
            life_path, soul_urge, birthday_number, expression_number
        )
    user_content = NUMEROLOGY_BLUEPRINT_USER.format(
        life_path=life_path,
        soul_urge=soul_urge,
        birthday_number=birthday_number,
        expression_number=expression_number,
    )
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BLUEPRINT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=800,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_numerology_blueprint(
                data, life_path, soul_urge, birthday_number, expression_number
            )
    except Exception as e:
        logger.warning("LLM numerology blueprint call failed: %s", e)
    return _fallback_numerology_blueprint(
        life_path, soul_urge, birthday_number, expression_number
    )


async def call_llm_for_numerology_narrative(
    life_path: int,
    soul_urge: int,
    birthday_number: int,
    expression_number: int,
    user_context: str | None = None,
) -> dict[str, Any]:
    """Generate full AI narrative for the actual Numerology test result."""
    if not settings.openai_api_key:
        return {
            "title": f"Numerology: Life Path {life_path}",
            "summary": "Your numbers reveal a path of discovery and growth.",
        }

    user_context = (user_context or "").strip()
    if user_context:
        user_context = "Known about this user:\n" + user_context
    else:
        user_context = ""

    input_json = json.dumps({
        "life_path": life_path,
        "soul_urge": soul_urge,
        "expression": expression_number,
        "birthday": birthday_number
    }, indent=2)

    user_content = NUMEROLOGY_NARRATIVE_USER.format(
        test_title="Numerology Profile",
        category="Numerology",
        user_context=user_context,
        input_json=input_json
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": NUMEROLOGY_NARRATIVE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1000,
            temperature=0.6,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_and_filter(data, NUMEROLOGY_NARRATIVE_JSON_KEYS)
    except Exception as e:
        logger.warning("LLM numerology narrative call failed: %s", e)
    return {}


_MBTI_TYPE_NAMES: dict[str, str] = {
    "INTJ": "The Architect", "INTP": "The Thinker", "ENTJ": "The Commander", "ENTP": "The Debater",
    "INFJ": "The Advocate", "INFP": "The Mediator", "ENFJ": "The Protagonist", "ENFP": "The Campaigner",
    "ISTJ": "The Logistician", "ISFJ": "The Defender", "ESTJ": "The Executive", "ESFJ": "The Consul",
    "ISTP": "The Virtuoso", "ISFP": "The Adventurer", "ESTP": "The Entrepreneur", "ESFP": "The Entertainer",
}

_MBTI_NARRATIVE_SYSTEM = """\
You are a compassionate, psychologically insightful personality coach writing for a mobile spiritual-wellness app.
Your writing is warm, reflective, and grounded in real psychology — never generic horoscope copy.
Always respond with ONLY valid JSON — no prose outside the JSON block.

Return this exact JSON shape:
{
  "title": "string — MBTI type name (e.g. 'The Architect')",
  "coreTraits": ["string — a short descriptive phrase, not a single word (e.g. 'You recharge alone, but care deeply about others')", "string — another short phrase", "string — etc."],
  "narrative": "string — 2-3 paragraphs separated by \\n\\n. Paragraph 1: core personality/theme. Paragraph 2: deeper dynamic/inner workings. Paragraph 3: life direction/patterns",
  "shortDescription": "string — a single paragraph summarizing the narrative, completely distinct from the paragraphs above",
  "strengths": ["string — a short phrase describing a strength (e.g. 'Deep spiritual insight')", "string — etc."],
  "challenges": ["string — a short phrase describing a challenge"],
  "spiritualInsight": "string — 1 sentence linking the personality type to inner growth"
}
"""


def _fallback_mbti_narrative(mbti_type: str) -> dict[str, Any]:
    name = _MBTI_TYPE_NAMES.get(mbti_type.upper(), "Your Type")
    return {
        "title": name,
        "coreTraits": [
            "You recharge alone, but care deeply about others",
            "You think ahead, looking for connections and meaning",
            "You're a mix of logic and emotional intelligence",
            "You prefer plans, but value integrity over control",
        ],
        "narrative": (
            f"As an {mbti_type}, you bring a unique blend of inner depth and outward expression. "
            "Your personality type is shaped by how you gather information and make decisions. "
            "You thrive in environments that respect your natural way of engaging with the world."
        ),
        "strengths": [
            "Deep intuitive thinking",
            "Strong personal principles",
            "High emotional intelligence",
        ],
        "challenges": [
            "Prone to perfectionism",
            "Occasional overthinking",
        ],
        "spiritualInsight": "Your growth path lies in balancing your inner world with the needs of the outer one.",
    }


async def call_llm_for_mbti_narrative(
    mbti_type: str,
    confidence: dict[str, int] | None = None,
    user_context: str | None = None,
) -> dict[str, Any]:
    """
    Generate MBTI personality narrative from a deterministically computed type.
    AI only writes the description — type is never determined by AI.
    """
    if not settings.openai_api_key:
        return _fallback_mbti_narrative(mbti_type)

    type_name = _MBTI_TYPE_NAMES.get(mbti_type.upper(), "")
    conf_lines = ""
    if confidence:
        conf_lines = "\n".join(f"  - {dim}: {pct}% dominant" for dim, pct in confidence.items())

    user_content = (
        f"MBTI Type: {mbti_type}{f' ({type_name})' if type_name else ''}\n"
        f"Dimension confidence:\n{conf_lines}\n"
        f"{f'User context: {user_context}' if user_context else ''}\n\n"
        "Write a short, reflective personality insight for this type. "
        "Highlight a balance of their strengths and a subtle inner tension. Keep it concise and readable on mobile."
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _MBTI_NARRATIVE_SYSTEM},
                {"role": "user", "content": _cap_input(user_content, 1500)},
            ],
            max_tokens=700,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data and isinstance(data, dict) and data.get("narrative"):
            return data
    except Exception as e:
        logger.warning("LLM MBTI narrative call failed: %s", e)
    return _fallback_mbti_narrative(mbti_type)
