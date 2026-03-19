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

def calculate_karmic_lessons(answers: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Karmic Lessons results based on quiz answers.
    Answers are expected to be in the format {"q1": val, "q2": val, "q3": val, ...}
    q3-q12 are 1-5 scales.
    
    Dimensions:
    boundaries = q3
    voice = q4
    trust = q5
    worthiness = q6
    control = q7
    patience = q8
    recurrence = q9, q10, q11, q12
    """
    # Helper to get numeric value from answer
    def get_val(q_key: str) -> float:
        val = answers.get(q_key)
        return _map_text_to_score(val)
    
    scores = {
        "boundaries": to_percent(get_val("q3")),
        "voice": to_percent(get_val("q4")),
        "trust": to_percent(get_val("q5")),
        "worthiness": to_percent(get_val("q6")),
        "control": to_percent(get_val("q7")),
        "patience": to_percent(get_val("q8"))
    }

    # Rank the lessons
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary = ranked[0][0]
    secondary = ranked[1][0]

    recurrence_score = to_percent(avg([
        get_val("q9"), get_val("q10"), get_val("q11"), get_val("q12")
    ]))

    title_map = {
        "boundaries": "The Lesson of Boundaries",
        "voice": "The Lesson of Voice",
        "trust": "The Lesson of Trust",
        "worthiness": "The Lesson of Worthiness",
        "control": "The Lesson of Surrender",
        "patience": "The Lesson of Divine Timing"
    }

    return {
        "primary_lesson": primary,
        "secondary_lesson": secondary,
        "title": title_map[primary],
        "recurrence_score": recurrence_score,
        "scores": scores,
        "answers": answers # Qualitative q1, q2
    }
