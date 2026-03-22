"""
Soul Compass: synthesis test combining values, motivations, fears, long-term desires.
Does not rely only on numerology. Output: { coreDrive, directionTheme, growthFocus, shadowPattern }.
Used as compute stub: extracts from answers (or LLM) into compact JSON; narrative uses only this JSON.
"""

from typing import Any


def compute_soul_compass(mind: int, heart: int, body: int, soul: int) -> dict[str, Any]:
    """
    Soul Compass alignment calculation.
    Inputs: 4 values (0-100).
    Returns average, imbalance, and alignment state.
    """
    average = round((mind + heart + body + soul) / 4)
    vals = [mind, heart, body, soul]
    imbalance = max(vals) - min(vals)

    if average >= 75 and imbalance <= 25:
        alignment_state = "Aligned"
    elif average >= 60:
        alignment_state = "Partial Alignment"
    else:
        alignment_state = "Misaligned"

    return {
        "mind": mind,
        "heart": heart,
        "body": body,
        "soul": soul,
        "alignment_score": average,
        "imbalance": imbalance,
        "alignment_state": alignment_state
    }
