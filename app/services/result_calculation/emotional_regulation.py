from typing import Any
from collections import Counter

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

def compute_emotional_regulation(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Calculate Emotional Regulation Type scores and identify primary/secondary types.
    
    Quiet containment: q1, q8, q12
    Reflective processor: q3, q9
    Expressive releaser: q2, q4, q7, q10
    Adaptive regulator: q5, q11
    """
    if isinstance(answers, dict):
        return answers

    # 1) Map answers to qX variables
    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}
    
    def get_ans(qid: int) -> float:
        return _map_text_to_score(ans_map.get(qid))

    def avg(lst):
        return sum(lst) / len(lst) if lst else 3.0

    def to_percent(avg_score):
        return int(round(((avg_score - 1) / 4) * 100))

    # 2) Calculate raw averages
    raw = {
        "containment": avg([get_ans(1), get_ans(8), get_ans(12)]),
        "reflective": avg([get_ans(3), get_ans(9)]),
        "expressive": avg([get_ans(2), get_ans(4), get_ans(7), get_ans(10)]),
        "adaptive": avg([get_ans(5), get_ans(11)]),
    }

    # 3) Convert to percent
    scores = {k: to_percent(v) for k, v in raw.items()}

    # 4) Rank types
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "containment": "Quiet Containment",
        "reflective": "Reflective Processor",
        "expressive": "Expressive Releaser",
        "adaptive": "Adaptive Regulator"
    }

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map[primary],
        "scores": scores
    }
