from typing import TypedDict, Any
try:
    from .astrology import compute_astrology
except ImportError:
    from app.services.result_calculation.astrology import compute_astrology

_SIGN_TO_ELEMENT = {
    "Aries": "Fire",
    "Taurus": "Earth",
    "Gemini": "Air",
    "Cancer": "Water",
    "Leo": "Fire",
    "Virgo": "Earth",
    "Libra": "Air",
    "Scorpio": "Water",
    "Sagittarius": "Fire",
    "Capricorn": "Earth",
    "Aquarius": "Air",
    "Pisces": "Water",
}

_SIGN_TO_MODALITY = {
    "Aries": "Cardinal",
    "Taurus": "Fixed",
    "Gemini": "Mutable",
    "Cancer": "Cardinal",
    "Leo": "Fixed",
    "Virgo": "Mutable",
    "Libra": "Cardinal",
    "Scorpio": "Fixed",
    "Sagittarius": "Mutable",
    "Capricorn": "Cardinal",
    "Aquarius": "Fixed",
    "Pisces": "Mutable",
}

class ZodiacElementModalityResult(TypedDict):
    dominant_element: str
    modality: str
    sun_sign: str
    moon_sign: str
    rising_sign: str

def calculate_zodiac_element_modality(birth_data: dict[str, Any]) -> ZodiacElementModalityResult | None:
    """
    Calculate the dominant element and modality based on the Big Three (Sun, Moon, Rising).
    """
    chart = compute_astrology(
        birth_year=birth_data.get("birth_year", 1990),
        birth_month=birth_data.get("birth_month", 1),
        birth_day=birth_data.get("birth_day", 1),
        birth_time=birth_data.get("birth_time"),
        birth_place_lat=birth_data.get("birth_place_lat", 0.0),
        birth_place_lng=birth_data.get("birth_place_lng", 0.0),
        birth_place_timezone=birth_data.get("birth_place_timezone", "UTC"),
    )
    
    if not chart:
        return None

    sun = str(chart.get("sun_sign", "") or "")
    moon = str(chart.get("moon_sign", "") or "")
    rising = str(chart.get("rising_sign", "") or "")

    elements = [
        _SIGN_TO_ELEMENT.get(sun),
        _SIGN_TO_ELEMENT.get(moon),
        _SIGN_TO_ELEMENT.get(rising)
    ]
    modalities = [
        _SIGN_TO_MODALITY.get(sun),
        _SIGN_TO_MODALITY.get(moon),
        _SIGN_TO_MODALITY.get(rising)
    ]

    # Clean None values
    elements = [e for e in elements if e]
    modalities = [m for m in modalities if m]

    if not elements or not modalities:
        return None

    def get_dominant(items: list[str], tie_breaker: str | None) -> str:
        counts: dict[str, int] = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        
        max_count = max(counts.values())
        candidates = [item for item, count in counts.items() if count == max_count]
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Tie breaker: use the one associated with the Sun sign
        if tie_breaker and tie_breaker in candidates:
            return tie_breaker
        
        # If Sun sign's trait isn't in candidates (rare with only 3 items), return first candidate
        return candidates[0]

    dominant_element = get_dominant(elements, _SIGN_TO_ELEMENT.get(sun))
    dominant_modality = get_dominant(modalities, _SIGN_TO_MODALITY.get(sun))

    return ZodiacElementModalityResult(
        dominant_element=dominant_element,
        modality=dominant_modality,
        sun_sign=sun,
        moon_sign=moon,
        rising_sign=rising
    )
