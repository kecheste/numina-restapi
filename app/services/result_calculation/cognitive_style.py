from typing import Any, Dict

def compute_cognitive_style(answers: list[Dict[str, Any]] | Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Cognitive Style (Analytical Empathy) dimensions.
    """
    if isinstance(answers, dict):
        return answers

    ans_map = {item.get("id") or item.get("question_id"): item.get("answer") for item in (answers or [])}

    def get_ans(qid: int) -> Any:
        return ans_map.get(qid)

    def to_float(val: Any) -> float:
        try: return float(val)
        except: return 3.0

    def get_choice_val(qid: int, target: str) -> float:
        val = get_ans(qid)
        if isinstance(val, str) and val.strip() == target:
            return 5.0
        return 1.0

    # Q1
    q1_a = get_choice_val(1, "Analyze recent events to deduce the cause")
    q1_b = get_choice_val(1, "Ask them directly how they feel")
    q1_c = get_choice_val(1, "Offer a practical suggestion")
    q1_d = get_choice_val(1, "Sit quietly and observe")

    # Q2
    q2_a = get_choice_val(2, "Research facts and data first")
    q2_b = get_choice_val(2, "Consider how people will feel")
    q2_c = get_choice_val(2, "Think about what will work best in practice")
    q2_d = get_choice_val(2, "Watch how the situation evolves")

    # Q3
    q3_a = get_choice_val(3, "Focus on the logical details")
    q3_b = get_choice_val(3, "Notice emotional tone and feelings")
    q3_c = get_choice_val(3, "Look for solutions")
    q3_d = get_choice_val(3, "Observe patterns and behavior")

    # Q4
    q4_a = get_choice_val(4, "Clarify the logical points")
    q4_b = get_choice_val(4, "Try to understand everyone's emotions")
    q4_c = get_choice_val(4, "Suggest a workable compromise")
    q4_d = get_choice_val(4, "Step back and watch before responding")

    scale_map = {
        "Strongly Disagree": 1.0,
        "Disagree": 2.0,
        "Neutral": 3.0,
        "Agree": 4.0,
        "Strongly Agree": 5.0
    }

    def get_scale_val(qid: int) -> float:
        val = get_ans(qid)
        if isinstance(val, str):
            mapped = scale_map.get(val.strip())
            if mapped is not None:
                return mapped
        return to_float(val)

    # Scales
    q5 = get_scale_val(5)
    q6 = get_scale_val(6)
    q7 = get_scale_val(7)
    q8 = get_scale_val(8)
    q9 = get_scale_val(9)
    q10 = get_scale_val(10)
    q11 = get_scale_val(11)
    q12 = get_scale_val(12)

    def avg(lst: list[float]) -> float:
        if not lst: return 3.0
        return sum(lst) / len(lst)

    analytical_avg = avg([q1_a, q2_a, q3_a, q4_a, q5, q10])
    empathic_avg = avg([q1_b, q2_b, q3_b, q4_b, q6, q11])
    practical_avg = avg([q1_c, q2_c, q3_c, q4_c, q7])
    observational_avg = avg([q1_d, q2_d, q3_d, q4_d, q8])
    balanced_avg = avg([q9, q12])

    def to_percent(avg_score: float) -> int:
        # Clamp bounds
        if avg_score < 1.0: avg_score = 1.0
        if avg_score > 5.0: avg_score = 5.0
        return int(round(((avg_score - 1) / 4) * 100))

    scores = {
        "analytical": to_percent(analytical_avg),
        "empathic": to_percent(empathic_avg),
        "practical": to_percent(practical_avg),
        "observational": to_percent(observational_avg),
        "balanced": to_percent(balanced_avg)
    }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else primary

    titles = {
        "analytical": "Analytical Thinker",
        "empathic": "Empathic Processor",
        "practical": "Practical Problem Solver",
        "observational": "Observational Strategist",
        "balanced": "Balanced Integrator"
    }

    return {
        "primary_style": primary,
        "secondary_style": secondary,
        "title": titles.get(primary, "Cognitive Style"),
        "scores": scores
    }
