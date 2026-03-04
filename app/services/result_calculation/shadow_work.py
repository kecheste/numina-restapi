"""
Shadow Work Lens: compute stub for text/slider answers.
Returns compact JSON: themes[], shadowTriggers[], coreBeliefs[], scores{}, nextSteps[].
Narrative LLM uses ONLY this JSON, not raw answers (keeps token usage low).
"""

from typing import Any


def compute_shadow_work(answers: list[Any] | dict[str, Any]) -> dict[str, Any]:
    """
    Stub: from answers (sliders + choices) produce structured JSON for narrative.
    Does not do heavy math; returns themes, shadowTriggers, coreBeliefs, scores, nextSteps.
    In production, scores can be derived from sliders; themes/beliefs from LLM extractor on raw text.
    """
    if isinstance(answers, dict):
        items = list(answers.values()) if answers else []
    else:
        items = list(answers) if answers else []

    # Slider answers (1-5) -> aggregate into simple scores
    slider_vals = []
    choice_texts = []
    for it in items:
        if isinstance(it, dict):
            a = it.get("answer", it)
            if isinstance(a, (int, float)):
                slider_vals.append(float(a))
            elif isinstance(a, str):
                choice_texts.append(a)
        elif isinstance(it, (int, float)):
            slider_vals.append(float(it))

    avg = sum(slider_vals) / len(slider_vals) if slider_vals else 3.0
    # Simple score mapping: higher slider avg = more engagement with shadow
    avoidance = max(0, min(10, 10 - (avg - 1) * 2.5))  # lower avg -> higher avoidance
    self_worth = max(0, min(10, (avg - 1) * 2.5))
    control = max(0, min(10, 10 - (avg - 1) * 2.0)) if slider_vals else 5.0
    trust = max(0, min(10, (avg - 1) * 2.5))

    themes = _infer_themes(slider_vals, choice_texts)
    shadow_triggers = _infer_shadow_triggers(choice_texts)
    core_beliefs = _infer_core_beliefs(choice_texts)
    next_steps = _infer_next_steps(themes, shadow_triggers)

    return {
        "themes": themes,
        "shadowTriggers": shadow_triggers,
        "coreBeliefs": core_beliefs,
        "scores": {
            "avoidance": round(avoidance, 1),
            "selfWorth": round(self_worth, 1),
            "control": round(control, 1),
            "trust": round(trust, 1),
        },
        "nextSteps": next_steps,
    }


def _infer_themes(slider_vals: list[float], choice_texts: list[str]) -> list[str]:
    themes = []
    combined = " ".join(choice_texts).lower()
    if not slider_vals or sum(slider_vals) / len(slider_vals) > 3:
        themes.append("Willingness to look at difficult emotions")
    if "anger" in combined or "frustration" in combined or "guilty" in combined:
        themes.append("Relationship with anger and guilt")
    if "creative" in combined or "afraid" in combined or "explore" in combined:
        themes.append("Creative expression and fear")
    if "inner critic" in combined or "judge" in combined or "harsh" in combined:
        themes.append("Inner critic and self-judgment")
    if "conflict" in combined or "rejection" in combined or "hold back" in combined:
        themes.append("Conflict avoidance and authenticity")
    if not themes:
        themes = ["Shadow awareness", "Emotional patterns", "Self-acceptance"]
    return themes[:5]


def _infer_shadow_triggers(choice_texts: list[str]) -> list[str]:
    triggers = []
    combined = " ".join(choice_texts).lower()
    if "calm down" in combined or "lecture" in combined:
        triggers.append("Being told to suppress emotions")
    if "push" in combined or "busy" in combined:
        triggers.append("Staying busy to avoid feeling")
    if "journal" in combined or "creatively" in combined:
        triggers.append("Vulnerability in expression")
    if "share" in combined or "trust" in combined:
        triggers.append("Being seen and dependent on others")
    if "never" in combined or "rarely" in combined:
        triggers.append("Checking in with difficult emotions")
    if not triggers:
        triggers = ["Uncertainty", "Rejection", "Loss of control"]
    return triggers[:5]


def _infer_core_beliefs(choice_texts: list[str]) -> list[str]:
    beliefs = []
    combined = " ".join(choice_texts).lower()
    if "safe" in combined and "hold" in combined:
        beliefs.append("I must be in control to be safe")
    if "ignore" in combined or "rarely" in combined:
        beliefs.append("My inner experience is not important")
    if "harsh" in combined or "shut out" in combined:
        beliefs.append("I am not good enough as I am")
    if "guide" in combined or "dialogue" in combined:
        beliefs.append("I can learn from my inner voice")
    if not beliefs:
        beliefs = ["Parts of me are unacceptable", "I need to hide to be loved"]
    return beliefs[:5]


def _infer_next_steps(themes: list[str], triggers: list[str]) -> list[str]:
    steps = [
        "Set aside 5 minutes daily to name one difficult emotion without judgment",
        "Notice one situation this week that triggers a shadow response",
        "Consider journaling or creative expression about one theme that showed up",
    ]
    if triggers:
        steps.append(f"Reflect on what underlies: {triggers[0]}")
    return steps[:5]
