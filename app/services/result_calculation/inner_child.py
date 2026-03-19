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

def calculate_inner_child(answers: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Inner Child Dialogue results based on quiz answers.
    Answers are expected to be in the format {"q1": val, "q2": val, "q3": val, ...}
    q3-q12 are 1-5 scales.
    """
    # Helper to get numeric value from answer
    def get_val(q_key: str) -> float:
        val = answers.get(q_key)
        return _map_text_to_score(val)
    
    raw = {
        "nurturer": avg([get_val("q3"), get_val("q8"), get_val("q10")]),
        "avoidant": avg([get_val("q4"), get_val("q9")]),
        "critic": get_val("q5"),
        "support": get_val("q6"),
        "awareness": avg([get_val("q7"), get_val("q11")]),
        "integrator": get_val("q12")
    }

    # Convert to percentages
    scores = {
        "nurturer": to_percent(raw["nurturer"]),
        "avoidant": to_percent(raw["avoidant"]),
        "critic": to_percent(raw["critic"]),
        "support": to_percent(raw["support"]),
        "awareness": to_percent(raw["awareness"]),
        "integrator": to_percent(raw["integrator"])
    }

    # Rank the types
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "nurturer": "Self-Nurturer",
        "avoidant": "Avoidant Protector",
        "critic": "Inner Critic",
        "support": "Support Seeker",
        "integrator": "Healing Integrator",
        "awareness": "Self-Aware Observer"
    }

    # Healing score is the average of integrator, nurturer, and awareness
    healing_score = int(round(
        (scores["integrator"] + scores["nurturer"] + scores["awareness"]) / 3
    ))

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map[primary],
        "healing_score": healing_score,
        "scores": scores,
        # Pass raw answers if needed by LLM for specific context
        "answers": answers
    }
