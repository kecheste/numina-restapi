from typing import Any

def avg(arr: list[float]) -> float:
    if not arr:
        return 0.0
    return sum(arr) / len(arr)

def to_percent(avg_score: float) -> int:
    """Map 1-5 scale to 0-100%."""
    return int(round(((avg_score - 1) / 4) * 100))

def _map_text_to_score(val: Any) -> float:
    if val is None:
        return 3.0
    
    mapping = {
        "strongly disagree": 1.0,
        "disagree": 2.0,
        "neutral": 3.0,
        "agree": 4.0,
        "strongly agree": 5.0
    }
    
    if isinstance(val, str):
        mapped = mapping.get(val.strip().lower())
        if mapped is not None:
            return mapped
    
    try:
        return float(val)
    except (ValueError, TypeError):
        return 3.0

def calculate_somatic_connection(answers: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Somatic Connection results based on quiz answers.
    Q3-Q12 are 1-5 scales.
    
    Mapping:
    somatic_listener = q3, q4, q5
    body_ignorer = q6, q9
    emotional_carrier = q8, q11
    integrated_regulator = q7, q10, q12
    """
    def get_val(q_key: str) -> float:
        val = answers.get(q_key)
        return _map_text_to_score(val)
    
    raw = {
        "listener": avg([get_val("q3"), get_val("q4"), get_val("q5")]),
        "ignorer": avg([get_val("q6"), get_val("q9")]),
        "carrier": avg([get_val("q8"), get_val("q11")]),
        "regulator": avg([get_val("q7"), get_val("q10"), get_val("q12")])
    }

    scores = {
        "listener": to_percent(raw["listener"]),
        "ignorer": to_percent(raw["ignorer"]),
        "carrier": to_percent(raw["carrier"]),
        "regulator": to_percent(raw["regulator"])
    }

    # Rank the types
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "listener": "Somatic Listener",
        "ignorer": "Body Ignorer",
        "carrier": "Emotional Carrier",
        "regulator": "Integrated Regulator"
    }

    # somatic_score = avg(listener, regulator)
    somatic_score = int(round(
        (scores["listener"] + scores["regulator"]) / 2
    ))

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map[primary],
        "somatic_score": somatic_score,
        "scores": scores,
        "answers": answers # Qualitative q1, q2
    }
