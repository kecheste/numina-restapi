import json
import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.prompts import (
    ASTROLOGY_BLUEPRINT_JSON_KEYS,
    ASTROLOGY_BLUEPRINT_USER,
    ASTROLOGY_CHART_NARRATIVE_JSON_KEYS,
    ASTROLOGY_CHART_NARRATIVE_SYSTEM,
    ASTROLOGY_CHART_NARRATIVE_USER,
    BLUEPRINT_SYSTEM,
    CHAKRA_ALIGNMENT_APPENDIX,
    CHAKRA_ALIGNMENT_JSON_KEYS,
    CHAKRA_PREVIEW_USER_APPENDIX,
    MIND_MIRROR_JSON_KEYS,
    MIND_MIRROR_SYSTEM,
    MIND_MIRROR_USER,
    ENERGY_ARCHETYPE_JSON_KEYS,
    ENERGY_ARCHETYPE_SYSTEM,
    ENERGY_ARCHETYPE_USER,
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
    HUMAN_DESIGN_JSON_KEYS,
    HUMAN_DESIGN_SYSTEM,
    HUMAN_DESIGN_USER,
    BIG_FIVE_SYSTEM,
    BIG_FIVE_USER,
    BIG_FIVE_JSON_KEYS,
    STARSEED_SYSTEM,
    STARSEED_USER,
    STARSEED_JSON_KEYS,
    CORE_VALUES_SYSTEM,
    CORE_VALUES_USER,
    CORE_VALUES_JSON_KEYS,
    EMOTIONAL_REGULATION_SYSTEM,
    EMOTIONAL_REGULATION_USER,
    EMOTIONAL_REGULATION_JSON_KEYS,
    SOUL_COMPASS_SYSTEM,
    SOUL_COMPASS_USER,
    SOUL_COMPASS_JSON_KEYS,
    TRANSITS_SYSTEM,
    TRANSITS_USER,
    TRANSITS_JSON_KEYS,
    MBTI_SYSTEM,
    MBTI_USER,
    MBTI_JSON_KEYS,
    ZODIAC_ELEMENT_MODALITY_USER,
    ZODIAC_ELEMENT_MODALITY_SYSTEM,
    ZODIAC_ELEMENT_MODALITY_JSON_KEYS,
    COGNITIVE_STYLE_SYSTEM,
    COGNITIVE_STYLE_USER,
    CHAKRA_ALIGNMENT_SYSTEM,
    CHAKRA_ALIGNMENT_USER,
    COGNITIVE_STYLE_JSON_KEYS,
    ENERGY_SYNTHESIS_SYSTEM,
    ENERGY_SYNTHESIS_USER,
    ENERGY_SYNTHESIS_JSON_KEYS,
    SOUL_URGE_SYSTEM,
    SOUL_URGE_USER,
    SOUL_URGE_JSON_KEYS,
)

logger = logging.getLogger(__name__)

from app.constants.human_design_maps import GATE_MEANING_MAP, GATE_PRIORITY

INPUT_MAX_CHARS = getattr(settings, "ai_input_max_chars", 3500)
TEST_RESULT_PROMPT_MAX_CHARS = 8000
OUTPUT_MAX_TOKENS = getattr(settings, "ai_result_output_max_tokens", 1000)


def _cap_input(text: str, max_chars: int | None = None) -> str:
    actual_max = int(max_chars or INPUT_MAX_CHARS)
    if len(text) <= actual_max:
        return text
    return text[: actual_max - 20] + "\n\n[...truncated]"


def _extract_json_from_response(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw.removeprefix("```json").strip()
    elif raw.startswith("```"):
        raw = raw.removeprefix("```").strip()
    
    if raw.endswith("```"):
        raw = raw.removesuffix("```").strip()
    
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
        "strengths", "challenges", "shadowPatterns", "coreTraits", "tryThis", "avoidThis",
        "yourBlueprint", "personalityConscious", "designUnconscious",
        "currentPatterns",
        "innerMotivations", "shadowExpression",
        "archetypeEchoes", "ancientGifts", "karmicShadows",
        "dailyEvolution", "suggestedReflection"
    )
    out = {}
    for k in allowed_keys:
        v = get_case_insensitive_val(obj, k)
        if v is None:
            continue
        if k in list_keys:
            if isinstance(v, list):
                out[k] = [str(x) for x in v][:8]
            elif isinstance(v, str) and v.strip().startswith("[") and v.strip().endswith("]"):
                try:
                    import ast
                    parsed = ast.literal_eval(v)
                    if isinstance(parsed, list):
                        out[k] = [str(x) for x in parsed][:8]
                    else:
                        out[k] = []
                except (ValueError, SyntaxError, NameError):
                    out[k] = []
            else:
                out[k] = []
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
    """Validate and normalize chakra test result: standard keys + strongestChakra + needsRebalancing + statusSummary + chakras (7 items) + synchronicities."""
    base = _validate_and_filter(obj, TEST_RESULT_JSON_KEYS | frozenset({"strongestChakra", "needsRebalancing", "statusSummary"}))
    
    if not base.get("statusSummary"): base["statusSummary"] = str(get_case_insensitive_val(obj, "statusSummary") or base.get("summary") or "").strip()
    if not base["statusSummary"]: base["statusSummary"] = "Your chakra balance reflects your current energy flow."
    if not base.get("strongestChakra"): base["strongestChakra"] = str(get_case_insensitive_val(obj, "strongestChakra") or "").strip()
    if not base.get("needsRebalancing"): base["needsRebalancing"] = str(get_case_insensitive_val(obj, "needsRebalancing") or "").strip()

    synch = get_case_insensitive_val(obj, "synchronicities")
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

    raw_chakras = get_case_insensitive_val(obj, "chakras")
    if not isinstance(raw_chakras, list): raw_chakras = []
    
    by_id: dict[str, dict[str, Any]] = {}
    for c in raw_chakras:
        if not isinstance(c, dict):
            continue
        cid = str(get_case_insensitive_val(c, "id") or "").strip().lower()
        if not cid:
            continue
        # Map IDs like "solar plexus" or "solar-plexus" to "solarPlexus"
        if "solar" in cid: cid = "solarPlexus"
        if "third" in cid or "eye" in cid: cid = "thirdEye"

        if cid in CHAKRA_IDS:
            by_id[cid] = {
                "id": cid,
                "name": str(get_case_insensitive_val(c, "name") or "").strip() or CHAKRA_NAMES[CHAKRA_IDS.index(cid)],
                "status": str(get_case_insensitive_val(c, "status") or "Balanced").strip(),
                "description": str(get_case_insensitive_val(c, "description") or "").strip() or "Energy flow for this center.",
                "tryItems": str(get_case_insensitive_val(c, "tryItems")).strip() if get_case_insensitive_val(c, "tryItems") else None,
                "avoidItems": str(get_case_insensitive_val(c, "avoidItems")).strip() if get_case_insensitive_val(c, "avoidItems") else None,
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
    if "extracted_json" not in base or not isinstance(base["extracted_json"], dict):
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

def _validate_mind_mirror_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize Mind Mirror result."""
    return _validate_and_filter(obj, MIND_MIRROR_JSON_KEYS)

async def call_llm_for_mind_mirror(responses: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """Dedicated LLM call for Mind Mirror analysis."""
    if not settings.openai_api_key:
        return _fallback_mind_mirror_json()

    user_content = MIND_MIRROR_USER.format(
        input_json=json.dumps(responses, indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MIND_MIRROR_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_mind_mirror_result(data)
    except Exception as e:
        logger.warning("LLM mind mirror call failed: %s", e)
    return _fallback_mind_mirror_json()

def _validate_energy_archetype_result(obj: Any) -> dict[str, Any]:
    return _validate_and_filter(obj, ENERGY_ARCHETYPE_JSON_KEYS)

async def call_llm_for_energy_archetype(responses: dict[str, Any]) -> dict[str, Any]:
    """Dedicated LLM call for Energy Archetype analysis."""
    if not settings.openai_api_key:
        return _fallback_energy_archetype_json()

    user_content = ENERGY_ARCHETYPE_USER.format(
        input_json=json.dumps(responses, indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ENERGY_ARCHETYPE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_energy_archetype_result(data)
    except Exception as e:
        logger.warning("LLM energy archetype call failed: %s", e)
    return _fallback_energy_archetype_json()


def _validate_energy_archetype_result(obj: Any, extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(obj, ENERGY_ARCHETYPE_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res

_PERSONALITY_WEIGHT = 1.0
_DESIGN_WEIGHT = 1.15


def _build_human_design_traits(hd_data: dict[str, Any]) -> dict[str, Any]:
    """Enrich Human Design data with gate meanings and weighted trait lists."""
    personality_gates = hd_data.get("personality_gates", {})
    design_gates = hd_data.get("design_gates", {})

    ordered_gate_entries: list[tuple[str, int | None, float]] = (
        [(f"personality_{p}", personality_gates.get(p), _PERSONALITY_WEIGHT) for p in GATE_PRIORITY[:2]]
        + [(f"design_{p}", design_gates.get(p), _DESIGN_WEIGHT) for p in GATE_PRIORITY[:2]]
        + [
            entry
            for planet in GATE_PRIORITY[2:]
            for entry in [
                (f"personality_{planet}", personality_gates.get(planet), _PERSONALITY_WEIGHT),
                (f"design_{planet}", design_gates.get(planet), _DESIGN_WEIGHT),
            ]
        ]
    )

    total = len(ordered_gate_entries)
    scored: list[tuple[float, str, int]] = []
    for idx, (label, gate, weight) in enumerate(ordered_gate_entries):
        if gate and gate in GATE_MEANING_MAP:
            score = (total - idx) * weight
            scored.append((score, label, gate))

    scored.sort(key=lambda x: x[0], reverse=True)

    seen_top: set[int] = set()
    top_gate_meanings = []
    for score, label, gate in scored:
        if gate not in seen_top:
            seen_top.add(gate)
            top_gate_meanings.append({
                "source": label,
                "gate": gate,
                "meaning": GATE_MEANING_MAP[gate].capitalize(),
                "score": round(score, 3)
            })
        if len(top_gate_meanings) == 8:
            break

    seen_p: set[str] = set()
    personality_traits: list[str] = []
    for _, label, gate in sorted(
        [(s, l, g) for s, l, g in scored if l.startswith("personality_")],
        key=lambda x: x[0], reverse=True
    ):
        meaning = GATE_MEANING_MAP[gate].capitalize()
        if meaning not in seen_p:
            seen_p.add(meaning)
            personality_traits.append(meaning)
        if len(personality_traits) == 5:
            break

    seen_d: set[str] = set()
    design_traits: list[str] = []
    for _, label, gate in sorted(
        [(s, l, g) for s, l, g in scored if l.startswith("design_")],
        key=lambda x: x[0], reverse=True
    ):
        meaning = GATE_MEANING_MAP[gate].capitalize()
        if meaning not in seen_d:
            seen_d.add(meaning)
            design_traits.append(meaning)
        if len(design_traits) == 5:
            break

    return {
        "top_gate_meanings": top_gate_meanings,
        "personality_traits": personality_traits,
        "design_traits": design_traits,
    }


async def call_llm_for_human_design(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Calculate Human Design insights via LLM."""
    if not settings.openai_api_key:
        return {
            "title": "Natural Origin",
            "summary": "Your Human Design reveals a unique energetic blueprint based on your birth data.",
            "energyBlueprint": "Explore your Type, Strategy, and Authority to understand how you naturally interact with the world.",
            "decisionGuidance": "Your specific authority provides a reliable way to make decisions that align with your true nature.",
        }


    traits = _build_human_design_traits(computed_input)
    computed_input.update(traits) # So they are saved in extracted_json

    user_content = HUMAN_DESIGN_USER.format(
        type=computed_input.get("type"),
        strategy=computed_input.get("strategy"),
        authority=computed_input.get("authority"),
        profile=computed_input.get("profile"),
        definition=computed_input.get("definition"),
        defined_centers=", ".join(computed_input.get("defined_centers", [])),
        undefined_centers=", ".join(computed_input.get("undefined_centers", [])),
        active_channels=", ".join(computed_input.get("active_channels", [])),
        incarnation_cross=json.dumps(computed_input.get("incarnation_cross", {})),
        personality_gates=json.dumps(computed_input.get("personality_gates", {}), indent=2),
        design_gates=json.dumps(computed_input.get("design_gates", {}), indent=2),
        top_gate_meanings=json.dumps(traits["top_gate_meanings"], indent=2),
        personality_traits=json.dumps(traits["personality_traits"], indent=2),
        design_traits=json.dumps(traits["design_traits"], indent=2),
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": HUMAN_DESIGN_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        return _validate_human_design_result(data, extracted=computed_input)
    except Exception as e:
        logger.exception("LLM human design call failed: %s", e)
        return {
            "title": "Natural Origin",
            "summary": "Your Human Design reveals a unique energetic blueprint. Explore your gates to understand your strategy.",
            "extracted_json": computed_input,
        }


def _validate_human_design_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, HUMAN_DESIGN_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res

async def call_llm_for_big_five(calculated_data: dict) -> dict:
    """Interpret Big Five results into a structured result."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        input_json = json.dumps(calculated_data, indent=2)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BIG_FIVE_SYSTEM},
                {"role": "user", "content": BIG_FIVE_USER.format(input_json=input_json)},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.6,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        return _validate_big_five_result(data or {}, extracted=calculated_data)
    except Exception as e:
        logger.warning("LLM Big Five call failed: %s", e)
        return {
            "title": "The Big Five Explorer",
            "summary": "Your Big Five profile revealed key insights into your natural tendencies. Explore your dimensions to understand your path.",
            "extracted_json": calculated_data,
        }

def _validate_big_five_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, BIG_FIVE_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res


def _fallback_starseed_result(calculated_data: dict) -> dict[str, Any]:
    primary = calculated_data.get("primary_origin", "Unknown")
    secondary = calculated_data.get("secondary_origin", "None")
    return {
        "title": "Your Starseed Origin",
        "originSummary": f"Your dominant resonance is with {primary} archetypal energy, modified by {secondary} influences.",
        "cosmicProfile": (
            f"Your cosmic signature suggests a primary alignment with {primary} themes, which define your core approach to reality. "
            f"The presence of {secondary} traits creates a unique modification of this path.\n\n"
            "A natural tension exists between your desire for cosmic expansion and the necessary grounding required for human existence, "
            "driving a recurring need to balance visionary goals with practical reality."
        ),
        "coreTraits": [
            "Resonant with higher-order patterns",
            "Synthesized understanding of diverse perspectives",
            "Adaptive response to complex environments",
        ],
        "strengths": ["Visionary Insight", "Pattern Recognition", "Intuitive Alignment"],
        "challenges": ["Cosmic Disconnection", "Grounding Friction", "Over-Sensitivity"],
        "spiritualInsight": "Your journey is about bridging the gap between vast potential and grounded manifestation.",
        "tryThis": ["Practice sensory grounding", "Document intuitive flashes", "Connect with nature regularly"],
        "avoidThis": ["Ignoring physical needs", "Escapism into abstraction"],
        "extracted_json": calculated_data
    }


async def call_llm_for_starseed(calculated_data: dict) -> dict:
    """Interpret Starseed Origins results into a structured result with grounded behavior."""
    if not settings.openai_api_key:
        return _fallback_starseed_result(calculated_data)

    resonance_scores = json.dumps(calculated_data.get("scores", {}), indent=2)
    user_content = STARSEED_USER.format(
        resonance_scores=resonance_scores,
        dominant_origin=calculated_data.get("primary_origin", "unknown"),
        secondary_influences=calculated_data.get("secondary_origin", "unknown"),
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": STARSEED_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_starseed_result(data, extracted=calculated_data)
    except Exception as e:
        logger.warning("LLM Starseed call failed: %s", e)
    return _fallback_starseed_result(calculated_data)


def _validate_starseed_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, STARSEED_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res


async def call_llm_for_core_values(calculated_data: dict) -> dict:
    """Interpret Core Values Sort results into a structured result."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt_content = CORE_VALUES_USER.replace("{primary_value}", str(calculated_data.get("primary_value", "unknown"))) \
                                        .replace("{secondary_value}", str(calculated_data.get("secondary_value", "unknown"))) \
                                        .replace("{third_value}", str(calculated_data.get("third_value", "unknown"))) \
                                        .replace("{scores}", json.dumps(calculated_data.get("scores", {}), indent=2))
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CORE_VALUES_SYSTEM},
                {"role": "user", "content": prompt_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.7,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        return _validate_core_values_result(data or {}, extracted=calculated_data)
    except Exception as e:
        logger.warning("LLM Core Values call failed: %s", e)
        return {
            "title": "Your Core Values",
            "summary": "Your core values drive your life decisions and sense of fulfillment. Explore your profile to understand your path.",
            "extracted_json": calculated_data,
        }


def _validate_core_values_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, CORE_VALUES_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res


def _validate_cognitive_style_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, COGNITIVE_STYLE_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res


async def call_llm_for_cognitive_style(calculated_data: dict) -> dict:
    """Interpret Cognitive Style results using the new sharpened tone prompt."""
    if not settings.openai_api_key:
        return {
            "title": "Natural Origin",
            "overview": "Your Cognitive Style reveals a unique way of processing information.",
            "extracted_json": calculated_data,
        }

    user_content = COGNITIVE_STYLE_USER.format(
        primary_style=calculated_data.get("primary_style", "unknown"),
        secondary_style=calculated_data.get("secondary_style", "unknown"),
        scores=json.dumps(calculated_data.get("scores", {}), indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COGNITIVE_STYLE_SYSTEM.format(
                    primary_style=calculated_data.get("primary_style", "unknown"),
                    secondary_style=calculated_data.get("secondary_style", "unknown"),
                    scores=json.dumps(calculated_data.get("scores", {}), indent=2)
                )},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.6,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        return _validate_cognitive_style_result(data, extracted=calculated_data)
    except Exception as e:
        logger.exception("LLM cognitive style call failed: %s", e)
        return {
            "title": "Your Thinking Style",
            "overview": "Your Cognitive Style result is being processed. It reveals how you naturally filter logic and intuition.",
            "extracted_json": calculated_data,
        }


def _fallback_energy_archetype_json() -> dict[str, Any]:
    return {
        "title": "The Harmonized Mind",
        "coreTraits": ["Balanced approach", "Integration of thought and feeling"],
        "strengths": ["Self-awareness", "Logical empathy", "Steady focus"],
        "challenges": ["Maintaining flow", "Decision fatigue", "Over-analysis"],
        "spiritualInsight": "Your journey is one of bridge-building between the seen and unseen, the logical and the intuitive.",
        "summary": "You possess a rare ability to synthesize information from both your head and your heart. This balance allows you to move through life with a sense of grounded purpose, even when external circumstances are chaotic.",
        "tryThis": [
            "Practice a daily check-in that balances logic and intuition",
            "Engage in activities that require both mental focus and physical awareness",
            "Study systems that integrate disparate fields of knowledge"
        ],
        "avoidThis": [
            "Falling into the trap of 'correctness' over resonance",
            "Dismissing subtle cues in favor of hard data"
        ],
        "extracted_json": {}
    }


def _fallback_mind_mirror_json() -> dict[str, Any]:
    return {
        "title": "Your Mind Mirror",
        "summary": "We are preparing a full reflective interpretation of your mental and emotional state.",
        "shortDescription": "A reflection of your current internal landscape is being prepared.",
        "mentalPattern": "We are identifying the dominant patterns in your current thinking.",
        "emotionalTone": "Your recent emotional state is being analyzed for deeper themes.",
        "currentImbalance": "We are looking for areas where your energy might be out of balance.",
        "hiddenInsight": "A deeper look into your responses is revealing subtle internal tensions.",
        "growthDirection": "A path for reconnection and balance is being formulated.",
        "coreTraits": ["Reflective", "Searching"],
        "strengths": ["Self-awareness", "Introspection"],
        "challenges": ["Mental pressure", "Finding balance"],
        "yourBlueprint": ["Regular reflection", "Emotional honesty", "Mind-body connection"],
        "tryThis": [
            "Journal about your top concern for 5 minutes",
            "Practice a short grounding breath exercise",
            "Notice where in your body you feel tension"
        ],
        "avoidThis": [
            "Over-analyzing without taking action",
            "Dismissing your emotional needs as 'extra'"
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

    input_str = _cap_input(input_str, max_chars=6000)
    user_content = TEST_RESULT_USER_TEMPLATE.format(
        test_title=test_title,
        category=category,
        input_json=input_str,
    )
    if include_chakra_preview:
        user_content = user_content + CHAKRA_PREVIEW_USER_APPENDIX
        user_content = user_content + CHAKRA_ALIGNMENT_APPENDIX
    if len(user_content) > TEST_RESULT_PROMPT_MAX_CHARS:
        user_content = user_content[: TEST_RESULT_PROMPT_MAX_CHARS - 20] + "\n\n[...truncated]"

    allowed_keys = (TEST_RESULT_JSON_KEYS | CHAKRA_ALIGNMENT_JSON_KEYS) if include_chakra_preview else TEST_RESULT_JSON_KEYS
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
        if k in ("coreTraits", "strengths", "challenges", "avoidThis", "tryThis"):
            out[k] = [str(x) for x in v][:8] if isinstance(v, list) else []
        else:
            s = str(v).strip() if v is not None and isinstance(v, str) else ""
            out[k] = s if s else fallback.get(k, "")
    return out


def _fallback_astrology_chart_narrative() -> dict[str, Any]:
    return {
        "title": "Your Astrology Chart",
        "coreTraits": ["Reflective", "Intuitive", "Grounded"],
        "sunSign": "Your sun sign shapes your core identity and how you direct your energy in the world.",
        "moonSign": "Your moon sign reveals your deepest emotional needs and how you process feelings in private.",
        "risingSign": "Your rising sign dictates your initial approach to new situations and how others first perceive you.",
        "astrologicalPattern": "Your chart blends your sun, moon, and rising signs into a unique energy signature.\n\nYou may feel tension between your desire for stability and your need for emotional depth.\n\nIn daily life, this plays out as a cautious approach to new relationships until you establish trust.",
        "strengths": ["Self-awareness", "Emotional depth", "Mentally adaptable"],
        "challenges": ["Integration", "Balance", "Emotional avoidance"],
        "tryThis": ["Journal by the moon", "Spend time in nature", "Practice grounding"],
        "avoidThis": ["Ignoring your body's needs", "Overthinking"],
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
    birth_day: int,
    expression_number: int,
) -> dict[str, Any]:
    """Ensure exactly 4 items: Life Path, Soul Urge, Birthday Number, Expression (with correct numbers)."""
    fallback = _fallback_numerology_blueprint(
        life_path, soul_urge, birth_day, expression_number
    )
    if not isinstance(obj, dict):
        return fallback
    items = obj.get("items")
    if not isinstance(items, list) or len(items) < 4:
        return fallback
    expected = [
        ("Life Path", life_path),
        ("Soul Urge", soul_urge),
        ("Birthday Number", birth_day),
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
    birth_day: int,
    expression_number: int,
) -> dict[str, Any]:
    return {
        "items": [
            {"number": str(life_path), "title": "Life Path", "description": "Your life path reflects your core purpose and lessons."},
            {"number": str(soul_urge), "title": "Soul Urge", "description": "Your soul urge reveals what your heart truly desires."},
            {"number": str(birth_day), "title": "Birthday Number", "description": "Your birthday number adds a personal layer to your cosmic profile."},
            {"number": str(expression_number), "title": "Expression", "description": "Your expression number reflects how you show up in the world."},
        ],
    }


async def call_llm_for_numerology_blueprint(
    life_path: int,
    soul_urge: int,
    birth_day: int,
    expression_number: int,
) -> dict[str, Any]:
    """Generate short AI copy for onboarding numerology blueprint screen."""
    if not settings.openai_api_key:
        return _fallback_numerology_blueprint(
            life_path, soul_urge, birth_day, expression_number
        )
    user_content = NUMEROLOGY_BLUEPRINT_USER.format(
        life_path=life_path,
        soul_urge=soul_urge,
        birth_day=birth_day,
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
                data, life_path, soul_urge, birth_day, expression_number
            )
    except Exception as e:
        logger.warning("LLM numerology blueprint call failed: %s", e)
    return _fallback_numerology_blueprint(
        life_path, soul_urge, birth_day, expression_number
    )


def _fallback_numerology_narrative(lp: int, su: int, bd: int, ex: int) -> dict[str, Any]:
    return {
        "title": "Your Numerology Profile",
        "corePattern": (
            f"Your numbers (Life Path {lp}, Soul Urge {su}, Birthday {bd}, Expression {ex}) create a unique energetic signature. "
            "The combination of your external direction and internal desires defines your natural approach to reality.\n\n"
            "A core tension exists between your need for structure and your drive for expansion, requiring a balanced perspective to navigate daily life."
        ),
        "lifePath": f"Life Path {lp} — Shapes your overall life direction and external journey.",
        "soulUrge": f"Soul Urge {su} — Reflects your internal desires and hidden motivations.",
        "expression": f"Expression {ex} — Highlights your natural abilities and behavioral gifts.",
        "birthday": f"Birthday {bd} — Dictates your daily personality tone and core strengths.",
        "coreTraits": [
            "Balanced approach to personal goals",
            "Synthesized understanding of situations",
            "Resilient response to change",
        ],
        "strengths": ["Integration", "Direction", "Alignment"],
        "challenges": ["Hesitation", "Pressure", "Conflict"],
        "spiritualInsight": "Your soul's journey involves mastering balance.",
        "tryThis": ["Identify conflicts", "Practice mindfulness", "Schedule spontaneity"],
        "avoidThis": ["Ignoring friction", "Over-committing"]
    }


async def call_llm_for_numerology_narrative(
    life_path: int,
    soul_urge: int,
    birth_day: int,
    expression_number: int,
    user_context: str | None = None,
) -> dict[str, Any]:
    """Generate full AI narrative for the actual Numerology test result with synthesized pattern."""
    if not settings.openai_api_key:
        return _fallback_numerology_narrative(life_path, soul_urge, birth_day, expression_number)

    user_content = NUMEROLOGY_NARRATIVE_USER.format(
        life_path=life_path,
        expression_number=expression_number,
        soul_urge=soul_urge,
        birth_day=birth_day,
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
            max_tokens=2000,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_and_filter(data, NUMEROLOGY_NARRATIVE_JSON_KEYS)
    except Exception as e:
        logger.warning("LLM numerology narrative call failed: %s", e)
    return _fallback_numerology_narrative(life_path, soul_urge, birth_day, expression_number)


_MBTI_TYPE_NAMES: dict[str, str] = {
    "INTJ": "The Architect", "INTP": "The Thinker", "ENTJ": "The Commander", "ENTP": "The Debater",
    "INFJ": "The Advocate", "INFP": "The Mediator", "ENFJ": "The Protagonist", "ENFP": "The Campaigner",
    "ISTJ": "The Logistician", "ISFJ": "The Defender", "ESTJ": "The Executive", "ESFJ": "The Consul",
    "ISTP": "The Virtuoso", "ISFP": "The Adventurer", "ESTP": "The Entrepreneur", "ESFP": "The Entertainer",
}

def _fallback_mbti_narrative(mbti_type: str) -> dict[str, Any]:
    return {
        "title": "Your Personality Type",
        "overview": (
            f"As an {mbti_type}, you process reality through a specific cognitive lens. "
            "Your natural way of gathering information and making decisions creates a consistent life pattern.\n\n"
            "Your dimension scores intensity often dictates whether your natural tendencies are fluid or more structured."
        ),
        "coreTraits": [
            "You process information internally but care about outcomes",
            "You seek patterns and logic in daily situations",
            "You balance structure with occasional spontaneity",
        ],
        "strengths": [
            "Deep intuitive processing",
            "Structured problem-solving",
            "Observant and grounded",
        ],
        "challenges": [
            "Can become rigid when stressed",
            "May overthink simple decisions",
            "Hesitant in unstructured environments",
        ],
        "cognitiveStyle": "You rely on proven frameworks while navigating external demands. Paragraph 1: How you process info. Paragraph 2: How you make decisions.",
        "tryThis": [
            "Pause before reacting to sudden changes",
            "Acknowledge the emotional context",
            "Experiment with breaking small routines"
        ],
        "avoidThis": [
            "Over-planning every detail",
            "Dismissing ideas that lack immediate proof"
        ]
    }


def _validate_mbti_result(data: dict[str, Any]) -> dict[str, Any]:
    res = _validate_and_filter(data, MBTI_JSON_KEYS)
    return res


async def call_llm_for_mbti_narrative(
    mbti_type: str,
    confidence: dict[str, int] | None = None,
    user_context: str | None = None,
) -> dict[str, Any]:
    """
    Generate MBTI personality narrative from a deterministically computed type.
    """
    if not settings.openai_api_key:
        return _fallback_mbti_narrative(mbti_type)

    type_name = _MBTI_TYPE_NAMES.get(mbti_type.upper(), "")
    conf_lines = ""
    if confidence:
        conf_lines = "\n".join(f"- {dim}: {pct}%" for dim, pct in confidence.items())

    user_content = MBTI_USER.format(
        mbti_type=f"{mbti_type}{f' ({type_name})' if type_name else ''}",
        confidence_lines=conf_lines or "Not available",
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MBTI_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.4,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            if not data.get("cognitiveStyle"):
                logger.warning("MBTI LLM response missing cognitiveStyle for type=%s", mbti_type)
            return _validate_mbti_result(data)
    except Exception as e:
        logger.warning("LLM MBTI call failed: %s", e)
    return _fallback_mbti_narrative(mbti_type)



def _fallback_emotional_regulation(primary: str, secondary: str) -> dict[str, Any]:
    return {
        "title": primary.replace("_", " ").title() if primary else "Emotional Regulation",
        "overview": "Your emotional regulation profile shows how you process and respond to inner feelings.",
        "strengths": ["Self-awareness", "Resilience", "Emotional depth"],
        "challenges": ["Over-processing", "Sudden surges"],
        "summary": f"Your primary style is {primary} with secondary traits of {secondary}." if primary and secondary else "Your emotional style is unique to you.",
        "tryThis": ["Daily mindfulness", "Journaling"],
        "avoidThis": ["Ignoring feelings", "Suppression"],
    }


async def call_llm_for_emotional_regulation(extracted: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_api_key:
        return _fallback_emotional_regulation(
            extracted.get("primary_type", ""), extracted.get("secondary_type", "")
        )

    user_content = EMOTIONAL_REGULATION_USER.format(
        primary_type=extracted.get("primary_type", ""),
        secondary_type=extracted.get("secondary_type", ""),
        scores=json.dumps(extracted.get("scores", {}), indent=2),
    )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EMOTIONAL_REGULATION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1000,
            temperature=0.5,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_and_filter(data, EMOTIONAL_REGULATION_JSON_KEYS)
    except Exception as e:
        logger.warning("LLM emotional regulation call failed: %s", e)
    return _fallback_emotional_regulation(
        extracted.get("primary_type", ""), extracted.get("secondary_type", "")
    )


async def call_llm_for_inner_child(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Interprets Inner Child Dialogue result via LLM."""
    if not settings.openai_api_key:
        return {
            "title": computed_input.get("title", "Inner Child Dialogue"),
            "summary": "Your Inner Child Dialogue result reveals your emotional patterns and healing potential.",
            "energyBlueprint": "Explore your primary and secondary types to understand your inner child's voice.",
        }

    from app.core.prompts import INNER_CHILD_SYSTEM, INNER_CHILD_USER, INNER_CHILD_JSON_KEYS

    answers = computed_input.get("answers", {})

    user_content = INNER_CHILD_USER.format(
        primary_type=computed_input.get("primary_type"),
        secondary_type=computed_input.get("secondary_type"),
        healing_score=computed_input.get("healing_score"),
        scores=json.dumps(computed_input.get("scores", {}), indent=2),
        q1=answers.get("q1", "N/A"),
        q2=answers.get("q2", "N/A"),
        q13=answers.get("q13", "N/A")
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": INNER_CHILD_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        res = _validate_and_filter(data, INNER_CHILD_JSON_KEYS)
        res["extracted_json"] = computed_input
        return res
    except Exception as e:
        logger.exception("LLM inner child call failed: %s", e)
        return {
            "title": computed_input.get("title", "Inner Child Dialogue"),
            "summary": "Your result reveals a unique emotional blueprint. Explore your traits to understand your healing journey.",
            "extracted_json": computed_input,
        }

async def call_llm_for_karmic_lessons(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Interprets Karmic Lessons result via LLM."""
    if not settings.openai_api_key:
        return {
            "title": computed_input.get("title", "The Lesson of Spiritual Growth"),
            "overview": "Your Karmic Lessons result reveals recurring life patterns and evolution opportunities.",
            "energyBlueprint": "Explore your primary and secondary lessons to understand your soul's journey.",
            "extracted_json": computed_input,
        }

    from app.core.prompts import KARMIC_LESSONS_SYSTEM, KARMIC_LESSONS_USER, KARMIC_LESSONS_JSON_KEYS

    answers = computed_input.get("answers", {})

    user_content = KARMIC_LESSONS_USER.format(
        primary_lesson=computed_input.get("primary_lesson"),
        secondary_lesson=computed_input.get("secondary_lesson"),
        title=computed_input.get("title"),
        recurrence_score=computed_input.get("recurrence_score"),
        scores=json.dumps(computed_input.get("scores", {}), indent=2),
        q1=answers.get("q1", "N/A"),
        q2=answers.get("q2", "N/A")
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": KARMIC_LESSONS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        res = _validate_and_filter(data, KARMIC_LESSONS_JSON_KEYS)
        res["extracted_json"] = computed_input
        return res
    except Exception as e:
        logger.exception("LLM karmic lessons call failed: %s", e)
        return {
            "title": computed_input.get("title", "Karmic Lessons"),
            "overview": "Your result reveals a unique spiritual blueprint. Explore your traits to understand your growth journey.",
            "extracted_json": computed_input,
        }

async def call_llm_for_past_life_vibes(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Interprets Past Life Vibes result via LLM."""
    if not settings.openai_api_key:
        return {
            "title": computed_input.get("title", "Ancient Archetype"),
            "soulNarrative": "Your Past Life Vibes result reveals your archetypal resonance.",
            "extracted_json": computed_input,
        }

    from app.core.prompts import PAST_LIFE_VIBES_SYSTEM, PAST_LIFE_VIBES_USER, PAST_LIFE_VIBES_JSON_KEYS

    answers = computed_input.get("answers", {})

    user_content = PAST_LIFE_VIBES_USER.format(
        primary_type=computed_input.get("primary_type"),
        secondary_type=computed_input.get("secondary_type"),
        resonance_score=computed_input.get("resonance_score"),
        scores=json.dumps(computed_input.get("scores", {}), indent=2),
        q1=answers.get("q1", "N/A"),
        q2=json.dumps(answers.get("q2", []), indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PAST_LIFE_VIBES_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        res = _validate_and_filter(data, PAST_LIFE_VIBES_JSON_KEYS)
        res["extracted_json"] = computed_input
        return res
    except Exception as e:
        return {
            "title": computed_input.get("title", "Past Life Vibes"),
            "soulNarrative": "Your result reveals a unique archetypal blueprint.",
            "extracted_json": computed_input,
        }

async def call_llm_for_somatic_connection(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Interprets Somatic Connection result via LLM."""
    if not settings.openai_api_key:
        return {
            "title": computed_input.get("title", "Somatic Awareness"),
            "overview": "Your Somatic Connection result reveals how you process emotions through your body.",
            "energyBlueprint": "Explore your primary and secondary types to understand your body's wisdom.",
            "extracted_json": computed_input,
        }

    from app.core.prompts import SOMATIC_SYSTEM, SOMATIC_USER, SOMATIC_JSON_KEYS

    answers = computed_input.get("answers", {})

    user_content = SOMATIC_USER.format(
        primary_type=computed_input.get("primary_type"),
        secondary_type=computed_input.get("secondary_type"),
        somatic_score=computed_input.get("somatic_score"),
        scores=json.dumps(computed_input.get("scores", {}), indent=2),
        q1=answers.get("q1", "N/A"),
        q2=answers.get("q2", "N/A")
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SOMATIC_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        res = _validate_and_filter(data, SOMATIC_JSON_KEYS)
        res["extracted_json"] = computed_input
        return res
    except Exception as e:
        logger.exception("LLM somatic connection call failed: %s", e)
        return {
            "title": computed_input.get("title", "Somatic Connection"),
            "overview": "Your result reveals a unique somatic blueprint. Explore your traits to understand your body's emotional archive.",
            "extracted_json": computed_input,
        }

async def call_llm_for_stress_balance(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Interprets Stress Balance Index result via LLM."""
    if not settings.openai_api_key:
        return {
            "title": computed_input.get("title", "Stress Balance"),
            "overview": "Your Stress Balance result reveals how you manage pressure and detect stress.",
            "energyBlueprint": "Explore your primary and secondary types to understand your stress-response patterns.",
            "extracted_json": computed_input,
        }

    from app.core.prompts import STRESS_BALANCE_SYSTEM, STRESS_BALANCE_USER, STRESS_BALANCE_JSON_KEYS

    answers = computed_input.get("answers", {})

    user_content = STRESS_BALANCE_USER.format(
        primary_type=computed_input.get("primary_type"),
        secondary_type=computed_input.get("secondary_type"),
        balance_score=computed_input.get("balance_score"),
        scores=json.dumps(computed_input.get("scores", {}), indent=2),
        q1=answers.get("q1", "N/A"),
        q2=answers.get("q2", "N/A"),
        q3=answers.get("q3", "N/A")
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": STRESS_BALANCE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        res = _validate_and_filter(data, STRESS_BALANCE_JSON_KEYS)
        res["extracted_json"] = computed_input
        return res
    except Exception as e:
        logger.exception("LLM stress balance call failed: %s", e)
        return {
            "title": computed_input.get("title", "Stress Balance"),
            "overview": "Your result reveals a unique stress blueprint. Explore your traits to understand how you handle pressure.",
            "extracted_json": computed_input,
        }


async def call_llm_for_chakra_alignment(formatted_answers: str, user_context: str) -> dict[str, Any]:
    """Calculate Chakra Alignment Scan results via dedicated LLM call."""
    if not settings.openai_api_key:
        return _fallback_chakra_alignment_json()

    from app.core.prompts import CHAKRA_ALIGNMENT_SYSTEM, CHAKRA_ALIGNMENT_USER

    user_content = CHAKRA_ALIGNMENT_USER.format(
        input_json=formatted_answers,
        user_context=user_context
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CHAKRA_ALIGNMENT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.4,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        return _validate_chakra_alignment_result(data)
    except Exception as e:
        logger.exception("LLM chakra alignment call failed: %s", e)
        return _fallback_chakra_alignment_json()

def _fallback_chakra_alignment_json() -> dict[str, Any]:
    """Robust fallback for Chakra Alignment Scan."""
    from app.core.prompts import CHAKRA_IDS, CHAKRA_NAMES
    out: dict[str, Any] = {
        "title": "Chakra Balance Profile",
        "summary": "Your energetic centers show a unique pattern of balance and focus. This result is being refined.",
        "shortDescription": "Your chakra alignment reflects your current behavioral momentum and emotional state.",
        "coreTraits": ["Energetic Awareness", "Balanced Focus", "Pattern Recognition", "Grounded Reflection"],
        "strengths": ["Self-Observation", "Behavioral Awareness", "Adaptive Energy"],
        "challenges": ["Consistent Alignment", "Deeper Integration", "Maintaining Balance"],
        "spiritualInsight": "Your journey is about observing how your internal state influences your external world.",
        "tryThis": ["Practice mindful observation", "Breathe into tension areas", "Observe your reactions"],
        "avoidThis": ["Ignoring physical signals", "Over-analyzing emotions"],
        "strongestChakra": "Your Root Chakra is currently your most grounded point.",
        "needsRebalancing": "Your throat center needs attention to improve clear expression.",
        "statusSummary": "Your chakra balance reflects your current energy flow.",
        "chakras": [
            {
                "id": cid,
                "name": CHAKRA_NAMES[i],
                "status": "Balanced",
                "description": "This center is operating in its normal state.",
                "tryItems": "Stay present with your sensations.",
                "avoidItems": "Ignoring subtle shifts."
            }
            for i, cid in enumerate(CHAKRA_IDS)
        ]
    }
    return out

async def call_llm_for_soul_compass(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Dedicated LLM call for Soul Compass interpretation."""
    if not settings.openai_api_key:
        return _fallback_soul_compass_json(computed_input)

    user_content = SOUL_COMPASS_USER.format(
        mind=computed_input.get("mind", 0),
        heart=computed_input.get("heart", 0),
        body=computed_input.get("body", 0),
        soul=computed_input.get("soul", 0),
        alignment_score=computed_input.get("alignment_score", 0),
        imbalance=computed_input.get("imbalance", 0),
        alignment_state=computed_input.get("alignment_state", "Unknown"),
        decision=computed_input.get("decision", "Not specified")
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SOUL_COMPASS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.6,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_soul_compass_result(data, extracted=computed_input)
    except Exception as e:
        logger.warning("LLM soul compass call failed: %s", e)
    return _fallback_soul_compass_json(computed_input)


def _validate_soul_compass_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, SOUL_COMPASS_JSON_KEYS)
    raw_aa = get_case_insensitive_val(data, "alignmentAnalysis")
    if isinstance(raw_aa, dict):
        res["alignmentAnalysis"] = {
            k: str(raw_aa.get(k, "")) for k in ("mind", "heart", "body", "soul")
        }
    elif isinstance(raw_aa, str):
        res["alignmentAnalysis"] = {k: raw_aa for k in ("mind", "heart", "body", "soul")}
    else:
        res["alignmentAnalysis"] = {k: "" for k in ("mind", "heart", "body", "soul")}
    if extracted:
        res["extracted_json"] = extracted
    return res


def _fallback_soul_compass_json(extracted: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Your Soul Compass",
        "decisionInsight": "Your internal compass is finding its orientation. The balance between your mind, heart, body, and soul suggests a path of integration and self-discovery.",
        "alignmentAnalysis": {
            "mind": "Your mind seeks clarity and logical structure.",
            "heart": "Your heart resonates with emotional truth.",
            "body": "Your body provides a grounded foundation.",
            "soul": "Your soul pulls toward deeper purpose."
        },
        "whatThisMeans": "You are in a process of aligning your internal dimensions to make a choice that resonates with your whole self.",
        "suggestedReflection": [
            "What does your intuition say in the quiet moments?",
            "Where do you feel the most resistance in your body?",
            "If you knew you could not fail, what would you choose?"
        ],
        "extracted_json": extracted
    }


async def call_llm_for_transits(computed_input: dict[str, Any]) -> dict[str, Any]:
    """Dedicated LLM call for Transit reading interpretation."""
    if not settings.openai_api_key:
        return _fallback_transits_json(computed_input)

    user_content = TRANSITS_USER.format(
        input_json=json.dumps(computed_input, indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TRANSITS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.5,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_transits_result(data, extracted=computed_input)
    except Exception as e:
        logger.warning("LLM transits call failed: %s", e)
    return _fallback_transits_json(computed_input)


def _validate_transits_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, TRANSITS_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res


def _fallback_transits_json(extracted: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Your Current Phase",
        "phaseDescription": (
            "The planetary movements are creating a notable backdrop to your life right now. "
            "Several transits are in contact with your natal chart, activating specific areas of experience.\n\n"
            "This is a period that calls for both awareness and intentional action. "
            "The themes being triggered are worth working with consciously rather than reacting to automatically."
        ),
        "currentPatterns": [
            "Shifts in your core identity and long-term sense of direction",
            "Heightened emotional responses and inner relational patterns",
            "Adjustments in the balance between effort and flow in daily life",
        ],
        "challenges": [
            "Impatience with the natural pace of change",
            "Tendency toward emotional reactivity in close relationships",
            "Internal pressure to resolve things before they are fully ready",
        ],
        "tryThis": [
            "Identify one area of your life where you can apply consistent effort this month",
            "Notice emotional reactions before responding — give yourself a beat",
            "Carve out time for reflection before making significant decisions",
        ],
        "avoidThis": [
            "Impulsive decisions driven by frustration or impatience",
            "Ignoring emotional signals in favor of pushing through",
        ],
        "spiritualInsight": "Working with the current energy rather than against it will produce the best results.",
        "extracted_json": extracted,
    }

def _validate_zodiac_element_modality_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize Zodiac Element & Modality result."""
    return _validate_and_filter(obj, ZODIAC_ELEMENT_MODALITY_JSON_KEYS)


async def call_llm_for_zodiac_element_modality(element: str, modality: str, astrology_context: str = "") -> dict[str, Any]:
    """Dedicated LLM call for Zodiac Element & Modality interpretation."""
    if not settings.openai_api_key:
        return _fallback_zodiac_element_modality_json(element, modality, astrology_context)

    user_content = ZODIAC_ELEMENT_MODALITY_USER.format(
        element=element,
        modality=modality,
        astrology_context=astrology_context or "No additional context available"
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ZODIAC_ELEMENT_MODALITY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=OUTPUT_MAX_TOKENS,
            temperature=0.6,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_from_response(raw)
        if data:
            return _validate_zodiac_element_modality_result(data)
    except Exception as e:
        logger.warning("LLM zodiac element modality call failed: %s", e)
    return _fallback_zodiac_element_modality_json(element, modality)


def _fallback_zodiac_element_modality_json(element: str, modality: str, astrology_context: str = "") -> dict[str, Any]:
    return {
        "title": f"The {modality} {element} Soul",
        "energyProfile": f"Your internal code is written in the language of {element} and executed with the drive of {modality} action. This creates a psychological foundation rooted in how you process energy and manifest intention.\n\nWith {element} as your primary resource, your energy flows with specific characteristics that are catalyzed by {modality} action. This interaction defines your unique operational style.",
        "coreTraits": [
            f"Strong {element} resonance",
            f"{modality} approach to action",
            "Balanced energetic signature",
            "Consistent behavioral output",
            "Adaptation to environmental flux"
        ],
        "strengths": ["Energetic clarity", "Type-specific focus", "Operational efficiency"],
        "challenges": ["Maintaining balance", "Processing intensity", "Contextual adaptation"],
        "shadowPattern": f"When misaligned, the {modality} drive can overwhelm the {element} resource, leading to a specific type of burnout or tactical inefficiency.",
        "dailyEvolution": [
            f"Notice when your {modality} drive is disconnected from your {element} state.",
            f"Practice grounding your {element} energy before taking {modality} action."
        ]
    }

def _validate_energy_synthesis_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, ENERGY_SYNTHESIS_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res

async def call_llm_for_energy_synthesis(calculated_data: dict) -> dict:
    """Interpret Energy Synthesis results using grounded tone."""
    if not settings.openai_api_key:
        return {
            "title": calculated_data.get("title", "Energy Synthesis"),
            "overview": "Your Energy Synthesis result is being processed. It reveals how you naturally integrate logic and emotion in your behavior.",
            "extracted_json": calculated_data,
        }

    user_content = ENERGY_SYNTHESIS_USER.format(
        primary_type=calculated_data.get("primary_type", "unknown"),
        secondary_type=calculated_data.get("secondary_type", "unknown"),
        integration_score=calculated_data.get("integration_score", 0),
        scores=json.dumps(calculated_data.get("scores", {}), indent=2)
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ENERGY_SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.6,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        return _validate_energy_synthesis_result(data, extracted=calculated_data)
    except Exception as e:
        logger.exception("LLM energy synthesis call failed: %s", e)
        return {
            "title": calculated_data.get("title", "Your Energy Synthesis"),
            "overview": "Your Energy Synthesis result could not be fully analyzed. It explores how you naturally integrate emotion and logic.",
            "extracted_json": calculated_data,
        }

def _validate_soul_urge_result(data: dict[str, Any], extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    res = _validate_and_filter(data, SOUL_URGE_JSON_KEYS)
    if extracted:
        res["extracted_json"] = extracted
    return res

async def call_llm_for_soul_urge(soul_urge_number: int, is_master: bool, source: str) -> dict:
    """Interpret Soul Urge (Heart's Desire) number."""
    calculated_data = {"soul_urge_number": soul_urge_number, "is_master": is_master, "source": source}
    if not settings.openai_api_key:
        return {
            "title": f"Soul Urge {soul_urge_number}",
            "coreDesire": "Your core desire interpretation is being processed.",
            "extracted_json": calculated_data,
        }

    user_content = SOUL_URGE_USER.format(
        soul_urge_number=soul_urge_number,
        is_master=is_master,
        source=source
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SOUL_URGE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.7,
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json_from_response(content) or {}
        return _validate_soul_urge_result(data, extracted=calculated_data)
    except Exception as e:
        logger.exception("LLM soul urge call failed: %s", e)
        return {
            "title": f"Soul Urge {soul_urge_number}",
            "coreDesire": "Your core desire interpretation could not be fully analyzed.",
            "extracted_json": calculated_data,
        }
