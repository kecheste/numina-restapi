"""
Transit reading compute using direct Swiss Ephemeris (swisseph).
Calculates natal and transit charts, and detects major aspects.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import swisseph as swe

logger = logging.getLogger(__name__)

# Standard standard planets for this calculation (Sun - Pluto)
PLANETS = {
    swe.SUN: "Sun",
    swe.MOON: "Moon",
    swe.MERCURY: "Mercury",
    swe.VENUS: "Venus",
    swe.MARS: "Mars",
    swe.JUPITER: "Jupiter",
    swe.SATURN: "Saturn",
    swe.URANUS: "Uranus",
    swe.NEPTUNE: "Neptune",
    swe.PLUTO: "Pluto",
}

# Major aspects and their target angles
ASPECTS = [
    (0, "Conjunction"),
    (60, "Sextile"),
    (90, "Square"),
    (120, "Trine"),
    (180, "Opposition"),
]

ORB = 6.0

def _get_julian_day(dt: datetime) -> float:
    """Helper to convert a UTC datetime to Julian Day (UT)."""
    return swe.julday(
        dt.year, 
        dt.month, 
        dt.day, 
        dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    )

def _get_planetary_positions(jd: float) -> dict[str, float]:
    """Helper to get tropical longitudes (0-360) for all standard planets."""
    positions = {}
    for body_id, name in PLANETS.items():
        # calc_ut returns (6 floats, error_msg). 
        # Index [0][0] is the longitude.
        res = swe.calc_ut(jd, body_id)
        positions[name.lower()] = res[0][0]
    return positions

def _calculate_aspects(transit_chart: dict[str, float], natal_chart: dict[str, float]) -> list[dict[str, Any]]:
    """Detects transiting aspects to natal planets based on defined orb."""
    detected = []
    for t_name, t_lon in transit_chart.items():
        for n_name, n_lon in natal_chart.items():
            # Angular difference (shortest distance on circle)
            diff = abs(t_lon - n_lon)
            if diff > 180:
                diff = 360 - diff
            
            for target_angle, aspect_name in ASPECTS:
                orb = abs(diff - target_angle)
                if orb <= ORB:
                    detected.append({
                        "transit_planet": t_name.capitalize(),
                        "natal_planet": n_name.capitalize(),
                        "aspect": aspect_name,
                        "orb": round(orb, 2),
                        "exact_angle": round(diff, 2)
                    })
    return detected

def compute_transits(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process transit reading input and return structured data for AI interpretation.
    
    Expected Input:
        - birth_datetime: ISO string (UTC)
        - latitude: float
        - longitude: float
    """
    birth_dt_str = input_data.get("birth_datetime")
    lat = input_data.get("latitude")
    lng = input_data.get("longitude")

    if not birth_dt_str:
        logger.error("compute_transits called without birth_datetime")
        return {"error": "Missing birth_datetime"}

    try:
        # 1. Prepare datetimes
        # Handle formats like '2023-10-27T10:00:00Z' or '2023-10-27T10:00:00+00:00'
        birth_dt = datetime.fromisoformat(birth_dt_str.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)

        # 2. Convert to Julian Day
        jd_natal = _get_julian_day(birth_dt)
        jd_transit = _get_julian_day(now_dt)

        # 3. Compute Positions (0-360°)
        natal_chart = _get_planetary_positions(jd_natal)
        transit_chart = _get_planetary_positions(jd_transit)

        # 4. Compute Houses (Optional, using Placidus)
        natal_houses = {}
        if lat is not None and lng is not None:
            # swe.houses returns (cusps_tuple, asmc_tuple)
            cusps, asmc = swe.houses(jd_natal, lat, lng, b'P')
            natal_houses = {f"House {i+1}": round(cusps[i], 4) for i in range(12)}
            natal_houses["Ascendant"] = round(asmc[0], 4)
            natal_houses["MC"] = round(asmc[1], 4)

        # 5. Detect Aspects
        transits = _calculate_aspects(transit_chart, natal_chart)

        return {
            "natal_chart": {k: round(v, 4) for k, v in natal_chart.items()},
            "transit_chart": {k: round(v, 4) for k, v in transit_chart.items()},
            "transits": transits,
            "natal_houses": natal_houses,
            "metadata": {
                "birth_datetime_utc": birth_dt.isoformat(),
                "calculation_time_utc": now_dt.isoformat(),
                "latitude": lat,
                "longitude": lng
            }
        }

    except Exception as e:
        logger.exception("Transit calculation failed: %s", e)
        return {"error": str(e)}
