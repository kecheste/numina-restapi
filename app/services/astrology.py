"""
Astrology chart calculation using Kerykeion (Swiss Ephemeris).
Uses birth date, time, and stored coordinates + timezone (no geocoding).
"""

from typing import TypedDict

from kerykeion import AstrologicalSubjectFactory

_SIGN_TO_ELEMENT = {
    "Aries": "fire",
    "Taurus": "earth",
    "Gemini": "air",
    "Cancer": "water",
    "Leo": "fire",
    "Virgo": "earth",
    "Libra": "air",
    "Scorpio": "water",
    "Sagittarius": "fire",
    "Capricorn": "earth",
    "Aquarius": "air",
    "Pisces": "water",
}

# Kerykeion may return abbreviated signs; map to full name for element lookup and display
_SIGN_ALIASES = {
    "ari": "Aries", "aries": "Aries",
    "tau": "Taurus", "taurus": "Taurus",
    "gem": "Gemini", "gemini": "Gemini",
    "can": "Cancer", "cancer": "Cancer",
    "leo": "Leo",
    "vir": "Virgo", "virgo": "Virgo",
    "lib": "Libra", "libra": "Libra",
    "sco": "Scorpio", "scorpio": "Scorpio", "scor": "Scorpio",
    "sag": "Sagittarius", "sagittarius": "Sagittarius",
    "cap": "Capricorn", "capricorn": "Capricorn",
    "aqu": "Aquarius", "aquarius": "Aquarius",
    "pis": "Pisces", "pisces": "Pisces",
}

def _normalize_sign(raw: str) -> str:
    """Return full sign name; leave as-is if already full or unknown."""
    if not raw:
        return ""
    key = raw.strip()
    if key in _SIGN_TO_ELEMENT:
        return key
    return _SIGN_ALIASES.get(key.lower(), key)


class ElementDistribution(TypedDict):
    fire: int
    earth: int
    air: int
    water: int


class AstrologyChartResult(TypedDict):
    sun_sign: str
    moon_sign: str
    rising_sign: str
    element_distribution: ElementDistribution


def _parse_birth_time(birth_time: str | None) -> tuple[int, int]:
    """Parse 'HH:MM' or 'HH:MM:SS' to (hour, minute). Default to noon if missing/invalid."""
    if not birth_time or not birth_time.strip():
        return 12, 0
    parts = birth_time.strip().split(":")
    try:
        hour = int(parts[0]) if parts else 12
        minute = int(parts[1]) if len(parts) > 1 else 0
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
        return hour, minute
    except (ValueError, TypeError):
        return 12, 0


def _element_distribution(sun_sign: str, moon_sign: str, rising_sign: str) -> ElementDistribution:
    """Build element counts from sun, moon, and rising signs."""
    counts: ElementDistribution = {"fire": 0, "earth": 0, "air": 0, "water": 0}
    for sign in (sun_sign, moon_sign, rising_sign):
        if sign and sign in _SIGN_TO_ELEMENT:
            elem = _SIGN_TO_ELEMENT[sign]
            counts[elem] += 1
    return counts


def compute_astrology(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_time: str | None,
    birth_place_lat: float,
    birth_place_lng: float,
    birth_place_timezone: str,
) -> AstrologyChartResult | None:
    """
    Compute natal chart: sun sign, moon sign, rising sign, element distribution.

    Uses stored coordinates and timezone (no geocoding). Returns None if
    required data is missing or calculation fails.
    """
    hour, minute = _parse_birth_time(birth_time)
    tz_str = (birth_place_timezone or "").strip() or "UTC"

    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name="User",
            year=birth_year,
            month=birth_month,
            day=birth_day,
            hour=hour,
            minute=minute,
            seconds=0,
            lng=birth_place_lng,
            lat=birth_place_lat,
            tz_str=tz_str,
            online=False,
            # Only compute what we need
            active_points=["Sun", "Moon", "Ascendant"],
        )
    except Exception:
        return None

    # Kerykeion: .sun.sign, .moon.sign; ascendant may be .first_house or .ascendant
    raw_sun = getattr(subject.sun, "sign", None) or ""
    raw_moon = getattr(subject.moon, "sign", None) or ""
    raw_rising = ""
    if hasattr(subject, "ascendant") and subject.ascendant is not None:
        raw_rising = getattr(subject.ascendant, "sign", None) or ""
    elif hasattr(subject, "first_house") and subject.first_house is not None:
        raw_rising = getattr(subject.first_house, "sign", None) or ""

    sun_sign = _normalize_sign(raw_sun)
    moon_sign = _normalize_sign(raw_moon)
    rising_sign = _normalize_sign(raw_rising)

    element_distribution = _element_distribution(sun_sign, moon_sign, rising_sign)

    return AstrologyChartResult(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        rising_sign=rising_sign,
        element_distribution=element_distribution,
    )
