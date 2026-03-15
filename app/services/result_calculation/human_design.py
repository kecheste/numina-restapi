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

    # 1️⃣ UTC conversion
    utc_dt = to_utc(birth_date, birth_time, timezone)

    # 2️⃣ Julian day
    jd_birth = julian_day(utc_dt)

    # 3️⃣ Design moment
    jd_design = solve_design_jd(jd_birth)

    # 4️⃣ Planet positions
    personality = planet_longitudes(jd_birth)
    design = planet_longitudes(jd_design)

    # 5️⃣ Gate mapping
    personality_gates = {
        k: longitude_to_gate(v)
        for k, v in personality.items()
    }

    design_gates = {
        k: longitude_to_gate(v)
        for k, v in design.items()
    }

    return {
        "utc_birth": utc_dt.isoformat(),
        "personality_gates": personality_gates,
        "design_gates": design_gates
    }
    