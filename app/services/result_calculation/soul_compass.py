"""
Soul Compass: synthesis test combining values, motivations, fears, long-term desires.
Does not rely only on numerology. Output: { coreDrive, directionTheme, growthFocus, shadowPattern }.
Used as compute stub: extracts from answers (or LLM) into compact JSON; narrative uses only this JSON.
"""

from typing import Any


def compute_soul_compass(answers: list[Any] | dict[str, Any]) -> dict[str, str]:
    """
    Stub/synthesis: from selected questions (values, motivations, fears, long-term desires)
    produce compact JSON for narrative. Returns coreDrive, directionTheme, growthFocus, shadowPattern.
    In production this can be an LLM extractor over raw answers; here we return structure from answers.
    """
    if isinstance(answers, dict):
        # Flatten for simple keyword scan
        text_parts = []
        for v in answers.values():
            if isinstance(v, str):
                text_parts.append(v)
            elif isinstance(v, list):
                text_parts.extend(str(x) for x in v)
        combined = " ".join(text_parts)
    else:
        combined = " ".join(
            str(a.get("answer", a) if isinstance(a, dict) else a) for a in (answers or [])
        ).lower()

    # Stub: derive simple themes from presence of keywords (can be replaced by LLM extractor)
    core_drive = _infer_core_drive(combined)
    direction_theme = _infer_direction_theme(combined)
    growth_focus = _infer_growth_focus(combined)
    shadow_pattern = _infer_shadow_pattern(combined)

    return {
        "coreDrive": core_drive,
        "directionTheme": direction_theme,
        "growthFocus": growth_focus,
        "shadowPattern": shadow_pattern,
    }


def _infer_core_drive(text: str) -> str:
    if "creat" in text or "express" in text or "art" in text:
        return "Creative expression and authenticity"
    if "help" in text or "service" in text or "other" in text:
        return "Service and connection with others"
    if "growth" in text or "learn" in text or "understand" in text:
        return "Growth and understanding"
    if "freedom" in text or "free" in text or "independ" in text:
        return "Freedom and independence"
    if "peace" in text or "balance" in text or "harmony" in text:
        return "Peace and balance"
    return "Purpose and meaning"


def _infer_direction_theme(text: str) -> str:
    if "spirit" in text or "soul" in text or "higher" in text:
        return "Spiritual alignment"
    if "relation" in text or "love" in text or "connect" in text:
        return "Relationship and belonging"
    if "career" in text or "work" in text or "calling" in text:
        return "Vocation and impact"
    if "heal" in text or "past" in text or "inner" in text:
        return "Healing and integration"
    return "Integration of inner and outer life"


def _infer_growth_focus(text: str) -> str:
    if "fear" in text or "anxiety" in text or "worry" in text:
        return "Working with fear and uncertainty"
    if "self-worth" in text or "worth" in text or "enough" in text:
        return "Self-worth and self-acceptance"
    if "boundary" in text or "say no" in text or "people-pleas" in text:
        return "Boundaries and saying no"
    if "trust" in text or "control" in text or "let go" in text:
        return "Trust and letting go"
    return "Integrating shadow and light"


def _infer_shadow_pattern(text: str) -> str:
    if "perfection" in text or "perfect" in text or "never enough" in text:
        return "Perfectionism and self-criticism"
    if "avoid" in text or "escape" in text or "numb" in text:
        return "Avoidance and numbing"
    if "control" in text or "need to control" in text:
        return "Over-control and rigidity"
    if "please" in text or "approval" in text or "rejection" in text:
        return "People-pleasing and approval-seeking"
    return "Unconscious patterns seeking integration"
