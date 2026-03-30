from typing import Any, Dict

def compute_cognitive_style(answers: list[Dict[str, Any]] | Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Cognitive Style dimensions.

    Scenario questions (q1-q4):
    - Each "A" answer adds +0.5 to analytical
    - Each "B" answer adds +0.5 to empathic
    - Each "C" answer adds +0.5 to practical
    - Each "D" answer adds +0.5 to observational

    Likert scales (q5-q12):
    - analytical: avg(q5, q10) + boost
    - empathic:   avg(q6, q11) + boost
    - practical:  q7 + boost
    - observational: q8 + boost
    - balanced:   avg(q9, q12)
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {
        item.get("id") or item.get("question_id"): item.get("answer")
        for item in (answers or [])
        if isinstance(item, dict)
    }

    _scenario_options: dict[int, dict[str, str]] = {
        1: {
            "Analyze recent events to deduce the cause": "A",
            "Ask them directly how they feel": "B",
            "Offer a practical suggestion": "C",
            "Sit quietly and observe": "D",
        },
        2: {
            "Research facts and data first": "A",
            "Consider how people will feel": "B",
            "Think about what will work best in practice": "C",
            "Watch how the situation evolves": "D",
        },
        3: {
            "Focus on the logical details": "A",
            "Notice emotional tone and feelings": "B",
            "Look for solutions": "C",
            "Observe patterns and behavior": "D",
        },
        4: {
            "Clarify the logical points": "A",
            "Try to understand everyone's emotions": "B",
            "Suggest a workable compromise": "C",
            "Step back and watch before responding": "D",
        },
    }

    boost = {"analytical": 0, "empathic": 0, "practical": 0, "observational": 0}
    _slot = {"A": "analytical", "B": "empathic", "C": "practical", "D": "observational"}

    for qid in [1, 2, 3, 4]:
        raw = ans_map.get(qid)
        if not isinstance(raw, str):
            continue
        letter = _scenario_options.get(qid, {}).get(raw.strip())
        if letter and letter in _slot:
            boost[_slot[letter]] += 1

    scale_map = {
        "Strongly Disagree": 1.0,
        "Disagree": 2.0,
        "Neutral": 3.0,
        "Agree": 4.0,
        "Strongly Agree": 5.0,
    }

    def get_scale(qid: int) -> float:
        val = ans_map.get(qid)
        if isinstance(val, str):
            mapped = scale_map.get(val.strip())
            if mapped is not None:
                return mapped
        try:
            return float(val)
        except (TypeError, ValueError):
            return 3.0

    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 3.0

    q5, q6, q7, q8, q9, q10, q11, q12 = (get_scale(i) for i in range(5, 13))

    raw_scores = {
        "analytical":    avg([q5, q10]) + boost["analytical"] * 0.5,
        "empathic":      avg([q6, q11]) + boost["empathic"] * 0.5,
        "practical":     q7             + boost["practical"] * 0.5,
        "observational": q8             + boost["observational"] * 0.5,
        "balanced":      avg([q9, q12]),
    }

    def to_percent(val: float) -> int:
        clamped = max(1.0, min(5.0, val))
        return int(round(((clamped - 1) / 4) * 100))

    scores = {k: to_percent(v) for k, v in raw_scores.items()}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else primary

    titles = {
        "analytical":    "Analytical Thinker",
        "empathic":      "Empathic Processor",
        "practical":     "Practical Problem Solver",
        "observational": "Observational Strategist",
        "balanced":      "Balanced Integrator",
    }

    return {
        "primary_style": primary,
        "secondary_style": secondary,
        "title": titles.get(primary, "Cognitive Style"),
        "scores": scores,
    }
