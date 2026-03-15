"""
Shadow Work Lens: compute stub for slider + single-choice answers.
Returns compact JSON: primary/secondary shadow, scores{}, qualitative fields.
Narrative LLM uses ONLY this JSON, not raw answers.
"""

from typing import Any


def compute_shadow_work(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Compute Shadow Work Lens scores (0-100) and identify shadow dimensions.

    Dimensions (slider q1-q7):
    - suppressed_expression: q1 (anger guilt), q4 (holding back), q6 (hidden gifts)
    - self_judgment:         q3 (self-judgment of impulses), q5 (mood shifts)
    - hidden_potential:      q2 (unexplored creativity), q7 (dream curiosity)

    Qualitative (single_choice q8-q10):
    - emotion_coping:   q8 — how they handle intense emotion
    - inner_critic:     q9 — relationship with inner critic
    - shadow_frequency: q10 — how often they check in with shadow emotions
    """
    if isinstance(answers, dict):
        items = answers
        def get_val(qid: int) -> Any:
            for k, v in items.items():
                try:
                    if int(''.join(filter(str.isdigit, str(k))) or 0) == qid:
                        return v.get("answer", v) if isinstance(v, dict) else v
                except Exception:
                    pass
            return None
    else:
        items_list = list(answers or [])
        def get_val(qid: int) -> Any:
            for it in items_list:
                if isinstance(it, dict):
                    if (it.get("id") or it.get("question_id")) == qid:
                        return it.get("answer")
            return None

    def to_float(val: Any) -> float:
        if val is None:
            return 3.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 3.0

    def to100(vals: list[float]) -> int:
        avg = sum(vals) / len(vals) if vals else 1.0
        return int(round(((avg - 1) / 4) * 100))

    # Slider scores (q1-q7)
    q = {i: to_float(get_val(i)) for i in range(1, 8)}

    scores = {
        "suppressed_expression": to100([q[1], q[4], q[6]]),
        "self_judgment":         to100([q[3], q[5]]),
        "hidden_potential":      to100([q[2], q[7]]),
    }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Qualitative answers passed through to LLM
    emotion_coping = get_val(8)
    inner_critic = get_val(9)
    shadow_frequency = get_val(10)

    return {
        "primary_shadow": ranked[0][0],
        "secondary_shadow": ranked[1][0],
        "scores": scores,
        "emotion_coping": str(emotion_coping) if emotion_coping else None,
        "inner_critic_relationship": str(inner_critic) if inner_critic else None,
        "shadow_check_in_frequency": str(shadow_frequency) if shadow_frequency else None,
    }
