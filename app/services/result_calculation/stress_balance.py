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

def calculate_stress_balance(answers: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Stress Balance Index results based on quiz answers.
    Q4-Q12 are 1-5 scales.
    
    Mapping:
    pressure_builder = q5, q7
    early_regulator = q4, q6, q9, q11
    emotional_releaser = q8
    shutdown = q10
    body_awareness = q12
    """
    def get_val(q_key: str) -> float:
        val = answers.get(q_key)
        return _map_text_to_score(val)
    
    raw = {
        "pressure_builder": avg([get_val("q5"), get_val("q7")]),
        "early_regulator": avg([get_val("q4"), get_val("q6"), get_val("q9"), get_val("q11")]),
        "emotional_releaser": get_val("q8"),
        "shutdown": get_val("q10")
    }

    scores = {
        "pressure_builder": to_percent(raw["pressure_builder"]),
        "early_regulator": to_percent(raw["early_regulator"]),
        "emotional_releaser": to_percent(raw["emotional_releaser"]),
        "shutdown": to_percent(raw["shutdown"])
    }

    # Rank the types
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "pressure_builder": "Pressure Builder",
        "early_regulator": "Early Regulator",
        "emotional_releaser": "Emotional Releaser",
        "shutdown": "Shutdown Responder"
    }

    # balance_score = avg(early_regulator, 100 - pressure_builder)
    balance_score = int(round(
        (scores["early_regulator"] + (100 - scores["pressure_builder"])) / 2
    ))

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map[primary],
        "balance_score": balance_score,
        "scores": scores,
        "answers": answers # Qualitative q1, q2, q3
    }
