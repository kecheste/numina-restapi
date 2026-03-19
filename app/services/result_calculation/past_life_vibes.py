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

def calculate_past_life_vibes(answers: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Past Life Vibes results based on quiz answers.
    Q3-Q12 are 1-5 scales.
    
    Mapping:
    healer = q4
    scholar = avg(q3, q10)
    warrior = q5
    mystic = avg(q6, q11)
    explorer = avg(q7, q12)
    builder = q8
    resonance = q9
    """
    def get_val(q_key: str) -> float:
        val = answers.get(q_key)
        return _map_text_to_score(val)
    
    raw = {
        "healer": get_val("q4"),
        "scholar": avg([get_val("q3"), get_val("q10")]),
        "warrior": get_val("q5"),
        "mystic": avg([get_val("q6"), get_val("q11")]),
        "explorer": avg([get_val("q7"), get_val("q12")]),
        "builder": get_val("q8")
    }

    scores = {
        "healer": to_percent(raw["healer"]),
        "scholar": to_percent(raw["scholar"]),
        "warrior": to_percent(raw["warrior"]),
        "mystic": to_percent(raw["mystic"]),
        "explorer": to_percent(raw["explorer"]),
        "builder": to_percent(raw["builder"])
    }

    # Rank the types
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "healer": "Ancient Healer",
        "scholar": "Wisdom Scholar",
        "warrior": "Guardian Warrior",
        "mystic": "Mystic Seer",
        "explorer": "Soul Explorer",
        "builder": "Sacred Builder"
    }

    resonance_score = int(round(
        (scores["mystic"] + scores["scholar"] + scores["healer"]) / 3
    ))

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map[primary],
        "resonance_score": resonance_score,
        "scores": scores,
        "answers": answers # Qualitative q1, q2
    }
