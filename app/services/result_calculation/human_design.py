from datetime import datetime
import pytz
import swisseph as swe

GATE_SIZE = 360 / 64.0

def to_utc(birth_date: str, birth_time: str, tz_name: str):
    tz = pytz.timezone(tz_name)

    local_dt = tz.localize(
        datetime.strptime(
            f"{birth_date} {birth_time}",
            "%Y-%m-%d %H:%M"
        )
    )

    return local_dt.astimezone(pytz.utc)

def julian_day(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour
        + dt_utc.minute / 60
        + dt_utc.second / 3600
    )

def solve_design_jd(jd_birth: float) -> float:
    target_arc = 88.0

    sun_birth = swe.calc_ut(jd_birth, swe.SUN)[0][0]

    jd = jd_birth
    step = 0.25

    while True:
        jd -= step
        sun_now = swe.calc_ut(jd, swe.SUN)[0][0]

        arc = (sun_birth - sun_now) % 360

        if arc >= target_arc:
            return jd

def planet_longitudes(jd: float):
    planets = {
        "sun": swe.SUN,
        "moon": swe.MOON,
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,
        "node": swe.MEAN_NODE,
    }

    result = {}

    for name, p in planets.items():
        result[name] = swe.calc_ut(jd, p)[0][0]

    result["earth"] = (result["sun"] + 180) % 360

    return result


def longitude_to_gate(lon: float):
    return int(lon // GATE_SIZE) + 1

def calculate_human_design(
    birth_date: str,
    birth_time: str,
    timezone: str,
    lat: float,
    lon: float
):
    """
    Core Human Design calculation pipeline
    """

    utc_dt = to_utc(birth_date, birth_time, timezone)

    jd_birth = julian_day(utc_dt)

    jd_design = solve_design_jd(jd_birth)

    personality = planet_longitudes(jd_birth)
    design = planet_longitudes(jd_design)

    def longitude_to_gate_and_line(lon: float):
        gate = int(lon // GATE_SIZE) + 1
        line = int((lon % GATE_SIZE) / (GATE_SIZE / 6)) + 1
        return gate, line

    personality_data = {
        k: longitude_to_gate_and_line(v)
        for k, v in personality.items()
    }
    design_data = {
        k: longitude_to_gate_and_line(v)
        for k, v in design.items()
    }

    personality_gates = {k: v[0] for k, v in personality_data.items()}
    design_gates = {k: v[0] for k, v in design_data.items()}

    CENTERS = {
        "Head": [64, 61, 63],
        "Ajna": [47, 24, 4, 17, 11, 43],
        "Throat": [62, 23, 56, 16, 20, 31, 8, 33, 45, 12, 35],
        "G": [1, 13, 25, 46, 2, 10, 15, 7],
        "Heart": [21, 40, 51, 26],
        "Solar Plexus": [6, 37, 22, 36, 49, 55, 30],
        "Sacral": [5, 14, 29, 34, 9, 3, 42, 52, 59],
        "Spleen": [48, 57, 44, 50, 32, 28, 18],
        "Root": [53, 60, 54, 19, 38, 39, 41, 58],
    }

    CHANNELS = [
        (64, 47, "Head", "Ajna"), (61, 24, "Head", "Ajna"), (63, 4, "Head", "Ajna"),
        (17, 62, "Ajna", "Throat"), (11, 56, "Ajna", "Throat"), (43, 23, "Ajna", "Throat"),
        (1, 8, "G", "Throat"), (7, 31, "G", "Throat"), (10, 20, "G", "Throat"), (13, 33, "G", "Throat"),
        (10, 57, "G", "Spleen"), (10, 34, "G", "Sacral"), (10, 15, "G", "G"), # 10-15 is G-G? actually 10-15 is G-G, but usually it's different centers. 

        (25, 51, "G", "Heart"), (2, 14, "G", "Sacral"), (15, 5, "G", "Sacral"), (46, 29, "G", "Sacral"),
        (21, 45, "Heart", "Throat"), (40, 37, "Heart", "Solar Plexus"), (51, 25, "Heart", "G"), (26, 44, "Heart", "Spleen"),
        (6, 59, "Solar Plexus", "Sacral"), (37, 40, "Solar Plexus", "Heart"), (22, 12, "Solar Plexus", "Throat"), (36, 35, "Solar Plexus", "Throat"),
        (49, 19, "Solar Plexus", "Root"), (55, 39, "Solar Plexus", "Root"), (30, 41, "Solar Plexus", "Root"),
        (5, 15, "Sacral", "G"), (14, 2, "Sacral", "G"), (29, 46, "Sacral", "G"), (34, 10, "Sacral", "G"), (34, 57, "Sacral", "Spleen"), (34, 20, "Sacral", "Throat"),
        (3, 60, "Sacral", "Root"), (9, 52, "Sacral", "Root"), (42, 53, "Sacral", "Root"), (59, 6, "Sacral", "Solar Plexus"), (50, 27, "Sacral", "Spleen"),
        (18, 58, "Spleen", "Root"), (28, 38, "Spleen", "Root"), (32, 54, "Spleen", "Root"), (44, 26, "Spleen", "Heart"), (50, 27, "Spleen", "Sacral"), (57, 10, "Spleen", "G"), (57, 34, "Spleen", "Sacral"), (57, 20, "Spleen", "Throat"), (48, 16, "Spleen", "Throat"),
        (53, 42, "Root", "Sacral"), (60, 3, "Root", "Sacral"), (52, 9, "Root", "Sacral"), (19, 49, "Root", "Solar Plexus"), (39, 55, "Root", "Solar Plexus"), (41, 30, "Root", "Solar Plexus"), (58, 18, "Root", "Spleen"), (38, 28, "Root", "Spleen"), (54, 32, "Root", "Spleen"),
    ]

    all_active_gates = set(personality_gates.values()) | set(design_gates.values())
    defined_centers = set()
    active_channels = []

    for g1, g2, c1, c2 in CHANNELS:
        if g1 in all_active_gates and g2 in all_active_gates:
            defined_centers.add(c1)
            defined_centers.add(c2)
            active_channels.append(f"{g1}-{g2}")

    undefined_centers = [c for c in CENTERS.keys() if c not in defined_centers]

    is_sacral_defined = "Sacral" in defined_centers
    is_sp_defined = "Solar Plexus" in defined_centers
    is_spleen_defined = "Spleen" in defined_centers
    is_heart_defined = "Heart" in defined_centers
    is_g_defined = "G" in defined_centers
    
    motors = ["Sacral", "Heart", "Solar Plexus", "Root"]
    defined_motors = [m for m in motors if m in defined_centers]

    def has_throat_motor_connection():
        motor_centers = set(defined_motors)
        if "Throat" not in defined_centers: return False
        for g1, g2, c1, c2 in CHANNELS:
            if g1 in all_active_gates and g2 in all_active_gates:
                if (c1 == "Throat" and c2 in motor_centers) or (c2 == "Throat" and c1 in motor_centers):
                    return True
        return False

    if not defined_centers:
        hd_type = "Reflector"
        strategy = "Wait for a lunar cycle"
        authority = "Lunar"
    elif is_sacral_defined:
        if has_throat_motor_connection():
            hd_type = "Manifesting Generator"
        else:
            hd_type = "Generator"
        strategy = "To respond"
        authority = "Emotional" if is_sp_defined else "Sacral"
    elif has_throat_motor_connection():
        hd_type = "Manifestor"
        strategy = "To inform"
        authority = "Emotional" if is_sp_defined else ("Splenic" if is_spleen_defined else "Ego Manifested")
    else:
        hd_type = "Projector"
        strategy = "Wait for the invitation"
        if is_sp_defined: authority = "Emotional"
        elif is_spleen_defined: authority = "Splenic"
        elif is_heart_defined: authority = "Ego Projected"
        elif is_g_defined: authority = "Self Projected"
        else: authority = "Mental"

    p_sun_line = personality_data["sun"][1]
    d_sun_line = design_data["sun"][1]
    profile = f"{p_sun_line}/{d_sun_line}"
    
    definition = "Single Definition"

    return {
        "utc_birth": utc_dt.isoformat(),
        "type": hd_type,
        "strategy": strategy,
        "authority": authority,
        "profile": profile,
        "definition": definition,
        "defined_centers": list(defined_centers),
        "undefined_centers": undefined_centers,
        "active_channels": active_channels,
        "personality_gates": personality_gates,
        "design_gates": design_gates
    }
    