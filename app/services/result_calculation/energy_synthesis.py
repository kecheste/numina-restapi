"""
Energy Synthesis: fusion type from primary axis (mind) and chakra heart status.
Now converted to a 12-question quiz.
"""

from typing import Any

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

def compute_energy_synthesis(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Compute Energy Synthesis from 12-question quiz measuring mind-heart integration.
    """
    if isinstance(answers, dict) and "heart_led" in answers:
        return answers # already computed

    # map answers to qX
    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or []) if isinstance(item, dict)}

    # Q1 and Q2 are situational, we primarily score Q3 - Q12
    # heart_led: q5
    # mind_led: avg(q6, q11)
    # sequential: avg(q3, q7)
    # unified: avg(q4, q8, q10, q12)
    # tension/conflict (optional usage in frontend): q9

    def get_ans(qid: int) -> float:
        return _map_text_to_score(ans_map.get(qid))
        
    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 3.0

    raw = {
        "heart_led": get_ans(5),
        "mind_led": avg([get_ans(6), get_ans(11)]),
        "sequential": avg([get_ans(3), get_ans(7)]),
        "unified": avg([get_ans(4), get_ans(8), get_ans(10), get_ans(12)]),
    }

    def to_percent(avg_score: float) -> int:
        return int(round(((avg_score - 1) / 4) * 100))

    scores = {
        "heart_led": to_percent(raw["heart_led"]),
        "mind_led": to_percent(raw["mind_led"]),
        "sequential": to_percent(raw["sequential"]),
        "unified": to_percent(raw["unified"]),
    }

    conflict_tension = to_percent(get_ans(9))
    scores["conflict_tension"] = conflict_tension

    # Rank them
    ranked = sorted(
        [(k, v) for k, v in scores.items() if k != "conflict_tension"],
        key=lambda x: x[1],
        reverse=True
    )
    
    primary = ranked[0][0]
    secondary = ranked[1][0]

    type_map = {
        "heart_led": "Heart-Led Navigator",
        "mind_led": "Mind-Led Strategist",
        "sequential": "Sequential Integrator",
        "unified": "Unified Synthesizer",
    }

    integration_score = int(round((scores["unified"] + scores["sequential"]) / 2))

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "title": type_map.get(primary, "Energy Synthesis"),
        "integration_score": integration_score,
        "scores": scores,
        "q1_rhythm": ans_map.get(1),
        "q2_cycle": ans_map.get(2),
    }

