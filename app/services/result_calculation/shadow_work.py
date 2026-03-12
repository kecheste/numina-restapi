"""
Shadow Work Lens: compute stub for text/slider answers.
Returns compact JSON: themes[], shadowTriggers[], coreBeliefs[], scores{}, nextSteps[].
Narrative LLM uses ONLY this JSON, not raw answers (keeps token usage low).
"""

from typing import Any


def compute_shadow_work(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Compute Shadow Work Lens scores (0-100) and rank primary/secondary shadows.
    Dimensions:
    - vulnerability_avoidance: a1, a2, a3
    - self_criticism: a4, a5, a6
    - emotional_suppression: a7, a8, a9
    - withdrawal_avoidance: a10, a11, a12
    """
    if isinstance(answers, dict):
        try:
            sorted_keys = sorted(answers.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            items = [answers[k] for k in sorted_keys]
        except Exception:
            items = list(answers.values())
    else:
        items = list(answers)

    vals = []
    for it in items:
        val = it.get("answer", it) if isinstance(it, dict) else it
        try:
            vals.append(float(val))
        except (ValueError, TypeError):
            vals.append(3.0) # Fallback

    while len(vals) < 12:
        vals.append(3.0)
    vals = vals[:12]

    def to100(lst: list[float]) -> int:
        avg = sum(lst) / len(lst) if lst else 1.0
        return int(round(((avg - 1) / 4) * 100))

    scores = {
        "vulnerability_avoidance": to100(vals[0:3]),
        "self_criticism": to100(vals[3:6]),
        "emotional_suppression": to100(vals[6:9]),
        "withdrawal_avoidance": to100(vals[9:12]),
    }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return {
        "primary_shadow": ranked[0][0],
        "secondary_shadow": ranked[1][0],
        "scores": scores
    }
