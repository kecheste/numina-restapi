"""
Human Design calculation engine.

Uses Swiss Ephemeris for planetary positions.
Implements the full Rave Mandala gate wheel, channel deduplication,
connected-component definition detection, south node, incarnation cross,
and correct type/strategy/authority determination.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pytz
import swisseph as swe


GATE_SIZE: float = 360.0 / 64.0  # 5.625° per gate

# I Ching / Rave Mandala gate sequence.
# Index 0 → Gate 41 starts at 0° within the wheel (= 300° tropical longitude).
# The sun transits Gate 41 around Jan 21-22, the start of the HD New Year.
GATE_ORDER: list[int] = [
    41, 19, 13, 49, 30, 55, 37, 63,
    22, 36, 25, 17, 21, 51, 42,  3,
    27, 24,  2, 23,  8, 20, 16, 35,
    45, 12, 15, 52, 39, 53, 62, 56,
    31, 33,  7,  4, 29, 59, 40, 64,
    47,  6, 46, 18, 48, 57, 32, 50,
    28, 44,  1, 43, 14, 34,  9,  5,
    26, 11, 10, 58, 38, 54, 61, 60,
]

# Gate 41 begins at Aquarius 0° = 300° tropical longitude.
WHEEL_START_LON: float = 300.0

# 9 energy centers and their member gates
CENTERS: dict[str, list[int]] = {
    "Head":         [64, 61, 63],
    "Ajna":         [47, 24,  4, 17, 11, 43],
    "Throat":       [62, 23, 56, 16, 20, 31,  8, 33, 45, 12, 35],
    "G":            [ 1, 13, 25, 46,  2, 10, 15,  7],
    "Heart":        [21, 40, 51, 26],
    "Solar Plexus": [ 6, 37, 22, 36, 49, 55, 30],
    "Sacral":       [ 5, 14, 29, 34,  9,  3, 42, 52, 59],
    "Spleen":       [48, 57, 44, 50, 32, 28, 18],
    "Root":         [53, 60, 54, 19, 38, 39, 41, 58],
}

# Build a gate → center lookup for fast access
_GATE_TO_CENTER: dict[int, str] = {
    gate: center
    for center, gates in CENTERS.items()
    for gate in gates
}

# All 36 canonical Human Design channels as (gate_a, gate_b) pairs.
# Stored with the lower gate number first for deduplication clarity.
_RAW_CHANNELS: list[tuple[int, int]] = [
    # Head → Ajna
    (47, 64), (24, 61), ( 4, 63),
    # Ajna → Throat
    (17, 62), (11, 56), (23, 43),
    # G → Throat
    ( 1,  8), ( 7, 31), (10, 20), (13, 33),
    # G → Spleen
    (10, 57),
    # G → Sacral
    ( 2, 14), (10, 34), (15,  5), (29, 46),
    # G → Heart
    (25, 51),
    # Heart → Throat
    (21, 45),
    # Heart → Solar Plexus
    (37, 40),
    # Heart → Spleen
    (26, 44),
    # Solar Plexus → Sacral
    ( 6, 59),
    # Solar Plexus → Throat
    (12, 22), (35, 36),
    # Solar Plexus → Root
    (19, 49), (39, 55), (30, 41),
    # Sacral → Throat
    (20, 34),
    # Sacral → Spleen
    (27, 50), (34, 57),
    # Sacral → Root
    ( 3, 60), ( 9, 52), (42, 53),
    # Sacral → Solar Plexus
    ( 6, 59),   # already listed; deduplication handles it
    # Spleen → Throat
    (16, 48), (20, 57),
    # Spleen → Root
    (18, 58), (28, 38), (32, 54),
    # Spleen → Heart
    (26, 44),  # already listed; deduplication handles it
]

def _build_channels() -> list[tuple[int, int, str, str]]:
    """
    Return a deduplicated list of (gate_a, gate_b, center_a, center_b) tuples.
    Each channel appears exactly once.  Channels whose gates share the same
    center (impossible in valid HD) are silently dropped.
    """
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, int, str, str]] = []
    for ga, gb in _RAW_CHANNELS:
        key = (min(ga, gb), max(ga, gb))
        if key in seen:
            continue
        seen.add(key)
        ca = _GATE_TO_CENTER.get(ga)
        cb = _GATE_TO_CENTER.get(gb)
        if ca and cb and ca != cb:
            result.append((ga, gb, ca, cb))
    return result


CHANNELS: list[tuple[int, int, str, str]] = _build_channels()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def to_utc(birth_date: str, birth_time: str, tz_name: str) -> datetime:
    tz = pytz.timezone(tz_name)
    local_dt = tz.localize(
        datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    )
    return local_dt.astimezone(pytz.utc)


def julian_day(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )


def solve_design_jd(jd_birth: float) -> float:
    """
    Find the Julian Day when the Sun was exactly 88° before its birth position.
    Uses a coarse walk (0.25 day steps) followed by a binary-search refinement
    to achieve ~0.001° angular accuracy (≈ a few minutes of time).
    """
    sun_birth = swe.calc_ut(jd_birth, swe.SUN)[0][0]

    def arc_at(jd: float) -> float:
        return (sun_birth - swe.calc_ut(jd, swe.SUN)[0][0]) % 360.0

    # Step backwards until we overshoot 88°
    jd = jd_birth
    step = 0.25
    while arc_at(jd) < 88.0:
        jd -= step

    # Binary-search refinement between jd (just past 88°) and jd+step
    lo, hi = jd, jd + step
    for _ in range(52):          # 52 iterations → < 0.0001 day accuracy
        mid = (lo + hi) / 2.0
        if arc_at(mid) < 88.0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def planet_longitudes(jd: float) -> dict[str, float]:
    """Return ecliptic tropical longitudes (0–360°) for all HD planets."""
    _planets = {
        "sun":     swe.SUN,
        "moon":    swe.MOON,
        "mercury": swe.MERCURY,
        "venus":   swe.VENUS,
        "mars":    swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn":  swe.SATURN,
        "uranus":  swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto":   swe.PLUTO,
        "node":    swe.MEAN_NODE,  # North Node
    }
    result: dict[str, float] = {}
    for name, body in _planets.items():
        result[name] = swe.calc_ut(jd, body)[0][0]

    # Derived bodies — treated as full activations
    result["earth"]      = (result["sun"]  + 180.0) % 360.0
    result["south_node"] = (result["node"] + 180.0) % 360.0
    return result


def longitude_to_gate_and_line(lon: float) -> tuple[int, int]:
    """
    Map an ecliptic longitude to the correct HD gate and line number.

    The Rave Mandala wheel starts at Gate 41 / 300° tropical longitude.
    Each of the 64 gates spans GATE_SIZE = 5.625°.
    Each gate is subdivided into 6 lines of GATE_SIZE/6 = 0.9375° each.
    """
    lon = lon % 360.0
    # Offset from wheel start, wrapped to [0, 360)
    offset = (lon - WHEEL_START_LON) % 360.0
    idx    = int(offset / GATE_SIZE)
    gate   = GATE_ORDER[idx]
    pos_in_gate = offset - idx * GATE_SIZE
    line   = min(int(pos_in_gate / (GATE_SIZE / 6.0)) + 1, 6)
    return gate, line


def determine_definition(
    defined_centers: set[str],
    adj: dict[str, set[str]],
) -> str:
    """
    Count the number of connected components among defined centers.
    Each component is a group of centers that are linked through active channels.
    """
    if not defined_centers:
        return "No Definition"

    visited: set[str] = set()
    components = 0
    for start in defined_centers:
        if start in visited:
            continue
        components += 1
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for nb in adj.get(node, set()):
                if nb in defined_centers and nb not in visited:
                    stack.append(nb)

    labels = {
        1: "Single Definition",
        2: "Split Definition",
        3: "Triple Split Definition",
        4: "Quad Split Definition",
    }
    return labels.get(components, f"{components}-Component Definition")


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate_human_design(
    birth_date: str,
    birth_time: str,
    timezone: str,
    lat: float,   # reserved — for future topocentric corrections
    lon: float,   # reserved — for future topocentric corrections
) -> dict[str, Any]:
    """
    Core Human Design calculation pipeline.

    Returns a dictionary suitable for LLM interpretation and front-end display.
    """

    # ── 1. Time ──────────────────────────────────────────────────────────────
    utc_dt   = to_utc(birth_date, birth_time, timezone)
    jd_birth = julian_day(utc_dt)
    jd_design = solve_design_jd(jd_birth)

    # ── 2. Planetary positions ────────────────────────────────────────────────
    personality_lons = planet_longitudes(jd_birth)
    design_lons      = planet_longitudes(jd_design)

    # ── 3. Gate + line for every activation ──────────────────────────────────
    personality_data: dict[str, tuple[int, int]] = {
        k: longitude_to_gate_and_line(v) for k, v in personality_lons.items()
    }
    design_data: dict[str, tuple[int, int]] = {
        k: longitude_to_gate_and_line(v) for k, v in design_lons.items()
    }

    personality_gates: dict[str, int] = {k: v[0] for k, v in personality_data.items()}
    design_gates: dict[str, int]      = {k: v[0] for k, v in design_data.items()}

    # ── 4. Active channels & defined centers ──────────────────────────────────
    all_active_gates: set[int] = (
        set(personality_gates.values()) | set(design_gates.values())
    )

    defined_centers: set[str] = set()
    active_channels: list[str] = []
    adj: dict[str, set[str]] = {c: set() for c in CENTERS}

    for g1, g2, c1, c2 in CHANNELS:
        if g1 in all_active_gates and g2 in all_active_gates:
            defined_centers.add(c1)
            defined_centers.add(c2)
            active_channels.append(f"{g1}-{g2}")
            adj[c1].add(c2)
            adj[c2].add(c1)

    undefined_centers: list[str] = [c for c in CENTERS if c not in defined_centers]

    # ── 5. Motor → Throat connectivity (BFS through defined centers) ──────────
    motors: set[str] = {"Sacral", "Heart", "Solar Plexus", "Root"}
    defined_motors: set[str] = motors & defined_centers

    def has_motor_to_throat() -> bool:
        if "Throat" not in defined_centers:
            return False
        visited: set[str] = {"Throat"}
        queue: list[str] = ["Throat"]
        while queue:
            curr = queue.pop(0)
            if curr in defined_motors:
                return True
            for nb in adj.get(curr, set()):
                if nb in defined_centers and nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return False

    motor_to_throat = has_motor_to_throat()

    # ── 6. Type & Strategy ────────────────────────────────────────────────────
    is_sacral_defined  = "Sacral"       in defined_centers
    is_sp_defined      = "Solar Plexus" in defined_centers
    is_spleen_defined  = "Spleen"       in defined_centers
    is_heart_defined   = "Heart"        in defined_centers
    is_g_defined       = "G"            in defined_centers

    if not defined_centers:
        hd_type  = "Reflector"
        strategy = "Wait for a lunar cycle"
        authority = "Lunar"

    elif is_sacral_defined:
        hd_type  = "Manifesting Generator" if motor_to_throat else "Generator"
        strategy = "To respond"
        authority = "Emotional" if is_sp_defined else "Sacral"

    elif motor_to_throat:
        hd_type  = "Manifestor"
        strategy = "To inform"
        if is_sp_defined:
            authority = "Emotional"
        elif is_spleen_defined:
            authority = "Splenic"
        else:
            authority = "Ego Manifested"

    else:
        hd_type  = "Projector"
        strategy = "Wait for the invitation"
        if is_sp_defined:
            authority = "Emotional"
        elif is_spleen_defined:
            authority = "Splenic"
        elif is_heart_defined:
            authority = "Ego Projected"
        elif is_g_defined:
            authority = "Self Projected"
        else:
            authority = "Mental"

    # ── 7. Profile (Personality Sun line / Design Sun line) ───────────────────
    profile = f"{personality_data['sun'][1]}/{design_data['sun'][1]}"

    # ── 8. Definition (connected components) ──────────────────────────────────
    definition = determine_definition(defined_centers, adj)

    # ── 9. Incarnation Cross ──────────────────────────────────────────────────
    incarnation_cross = {
        "personality_sun":   personality_gates["sun"],
        "personality_earth": personality_gates["earth"],
        "design_sun":        design_gates["sun"],
        "design_earth":      design_gates["earth"],
    }

    # ── 10. Result ────────────────────────────────────────────────────────────
    return {
        "utc_birth":        utc_dt.isoformat(),
        "type":             hd_type,
        "strategy":         strategy,
        "authority":        authority,
        "profile":          profile,
        "definition":       definition,
        "incarnation_cross": incarnation_cross,
        "defined_centers":  list(defined_centers),
        "undefined_centers": undefined_centers,
        "active_channels":  active_channels,
        "personality_gates": personality_gates,
        "design_gates":     design_gates,
    }