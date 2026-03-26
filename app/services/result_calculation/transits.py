"""Transit reading compute: derives active_themes from natal + current_transits + major_aspects."""

from typing import Any


def compute_transits(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process transit reading input and return structured data for LLM interpretation.

    Accepts:
        input_data: dict with keys:
            - natal: { sun_sign, moon_sign, rising_sign }
            - current_transits: { sun_sign, moon_sign, mercury_sign, venus_sign,
                                   mars_sign, jupiter_sign, saturn_sign }
            - major_aspects: list of { transit_planet, natal_point, aspect, orb }

    Returns:
        {
            natal, current_transits, major_aspects,
            active_themes: list[str]  (deduplicated, ordered)
        }
    """
    active_themes: list[str] = []

    for aspect in input_data.get("major_aspects") or []:
        transit_planet = aspect.get("transit_planet", "")
        natal_point = aspect.get("natal_point", "")

        if transit_planet == "Saturn" and natal_point == "Sun":
            active_themes.append("discipline, maturity, long-term direction")
        if transit_planet == "Mars" and natal_point == "Moon":
            active_themes.append("emotional reactivity, impatience, inner tension")
        if transit_planet == "Jupiter":
            active_themes.append("expansion, opportunities, movement")
        if transit_planet == "Venus":
            active_themes.append("relationships, harmony, attraction")
        if transit_planet == "Mercury":
            active_themes.append("thinking, communication, decisions")

    # Deduplicate while preserving insertion order
    seen: set[str] = set()
    deduped_themes: list[str] = []
    for theme in active_themes:
        if theme not in seen:
            seen.add(theme)
            deduped_themes.append(theme)

    return {
        "natal": input_data.get("natal") or {},
        "current_transits": input_data.get("current_transits") or {},
        "major_aspects": input_data.get("major_aspects") or [],
        "active_themes": deduped_themes,
    }
