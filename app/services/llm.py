"""
LLM calls with input cap and strict JSON output. Used for test result and synthesis.
"""

import json
import logging
from typing import Any

from app.core.config import settings
from app.core.prompts import (
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


async def call_llm_for_test_result(
    computed_input: dict[str, Any] | list[Any],
    test_title: str,
    category: str,
    user_context: str = "",
) -> dict[str, Any]:
    """
    Single LLM call: input is capped; output is strict JSON with title, summary, coreTraits,
    strengths, challenges, spiritualInsight, tryThis, avoidThis, synchronicities.
    Total user prompt capped to ~2000 tokens. Returns validated dict or fallback.
    """
    if not settings.openai_api_key:
        return _fallback_test_result_json()

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
    if len(user_content) > TEST_RESULT_PROMPT_MAX_CHARS:
        user_content = user_content[: TEST_RESULT_PROMPT_MAX_CHARS - 20] + "\n\n[...truncated]"

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TEST_RESULT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=min(settings.ai_max_tokens_per_request, OUTPUT_MAX_TOKENS),
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_and_filter(data, TEST_RESULT_JSON_KEYS)
    except Exception as e:
        logger.warning("LLM test result call failed: %s", e)
    return _fallback_test_result_json()


def _fallback_test_result_json() -> dict[str, Any]:
    return {
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
