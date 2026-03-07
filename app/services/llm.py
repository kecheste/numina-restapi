"""
LLM calls with input cap and strict JSON output. Used for test result and synthesis.
"""

import json
import logging
from typing import Any

from app.core.config import settings
from app.core.prompts import (
    ASTROLOGY_BLUEPRINT_JSON_KEYS,
    ASTROLOGY_BLUEPRINT_USER,
    BLUEPRINT_SYSTEM,
    CHAKRA_ALIGNMENT_APPENDIX,
    CHAKRA_PREVIEW_JSON_KEYS,
    CHAKRA_PREVIEW_USER_APPENDIX,
    NUMEROLOGY_BLUEPRINT_JSON_KEYS,
    NUMEROLOGY_BLUEPRINT_USER,
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
OUTPUT_MAX_TOKENS = getattr(settings, "ai_result_output_max_tokens", 600)


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


def _validate_and_filter(obj: dict[str, Any], allowed_keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    list_keys = (
        "insights", "recommendations", "sureThings", "growthAreas", "themes",
        "strengths", "shadowPatterns", "coreTraits", "tryThis", "avoidThis",
    )
    out = {}
    for k in allowed_keys:
        if k not in obj:
            continue
        v = obj[k]
        if k in list_keys:
            out[k] = [str(x) for x in v][:8] if isinstance(v, list) else []
        elif k == "synchronicities":
            if isinstance(v, list):
                out[k] = [
                    {"test": str(s.get("test", "")), "connection": str(s.get("connection", ""))}
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


def _validate_astrology_blueprint(obj: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_astrology_blueprint()
    if not isinstance(obj, dict):
        return fallback
    out: dict[str, Any] = {}
    for k in ASTROLOGY_BLUEPRINT_JSON_KEYS:
        v = obj.get(k)
        s = str(v).strip() if v is not None and isinstance(v, str) else ""
        out[k] = s if s else fallback[k]
    return out


def _fallback_astrology_blueprint() -> dict[str, Any]:
    return {
        "sunDescription": "Your sun sign shapes your core personality and life direction.",
        "moonDescription": "Your moon sign reveals how you process emotions and seek comfort.",
        "risingDescription": "Your rising sign reflects how others see you and your outward style.",
        "cosmicTraitsSummary": "🜂 Element: —\n☌ Modality: —\n♇ Ruling Planet: —\n🌠 Most active house: —",
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
    user_content = ASTROLOGY_BLUEPRINT_USER.format(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        rising_sign=rising_sign,
        fire=fire,
        earth=earth,
        air=air,
        water=water,
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
            max_tokens=400,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_astrology_blueprint(data)
    except Exception as e:
        logger.warning("LLM astrology blueprint call failed: %s", e)
    return _fallback_astrology_blueprint()


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


def _validate_numerology_blueprint(obj: dict[str, Any], life_path: int, soul_urge: int) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return _fallback_numerology_blueprint(life_path, soul_urge)
    items = obj.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return _fallback_numerology_blueprint(life_path, soul_urge)
    out_items: list[dict[str, str]] = []
    for i in items[:5]:
        if not isinstance(i, dict):
            continue
        n = i.get("number")
        t = i.get("title")
        d = i.get("description")
        if n is not None and t is not None and d is not None:
            out_items.append({
                "number": str(n),
                "title": str(t),
                "description": _truncate_numerology_description(str(d)),
            })
    if not out_items:
        return _fallback_numerology_blueprint(life_path, soul_urge)
    return {"items": out_items}


def _fallback_numerology_blueprint(life_path: int, soul_urge: int) -> dict[str, Any]:
    return {
        "items": [
            {"number": str(life_path), "title": "Life Path", "description": "Your life path reflects your core purpose and lessons."},
            {"number": str(soul_urge), "title": "Soul Urge", "description": "Your soul urge reveals what your heart truly desires."},
        ],
    }


async def call_llm_for_numerology_blueprint(
    life_path: int,
    soul_urge: int,
) -> dict[str, Any]:
    """Generate short AI copy for onboarding numerology blueprint screen."""
    if not settings.openai_api_key:
        return _fallback_numerology_blueprint(life_path, soul_urge)
    user_content = NUMEROLOGY_BLUEPRINT_USER.format(
        life_path=life_path,
        soul_urge=soul_urge,
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
            max_tokens=400,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_numerology_blueprint(data, life_path, soul_urge)
    except Exception as e:
        logger.warning("LLM numerology blueprint call failed: %s", e)
    return _fallback_numerology_blueprint(life_path, soul_urge)
