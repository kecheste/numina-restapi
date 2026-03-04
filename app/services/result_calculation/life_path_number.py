"""
Life Path Number: computed from date of birth.
Sum all digits of YYYY-MM-DD, reduce to 1–9 or keep master numbers 11, 22, 33.
Returns JSON: { lifePath, traits[], strengths[], challenges[] }.
"""

from typing import Any

# Master numbers are not reduced
MASTER_NUMBERS = (11, 22, 33)


def _reduce_to_life_path(n: int) -> int:
    """Reduce to single digit, but keep 11, 22, 33 as master numbers."""
    while n > 9:
        if n in MASTER_NUMBERS:
            return n
        n = sum(int(d) for d in str(n))
    return n if n >= 1 else 0


def compute_life_path_number(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
) -> dict[str, Any] | None:
    """
    Compute life path from birth date. Returns dict with lifePath (int),
    traits[], strengths[], challenges[]. Returns None if date invalid.
    """
    date_str = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"
    digits = [int(d) for d in date_str if d.isdigit()]
    if not digits:
        return None
    life_path = _reduce_to_life_path(sum(digits))

    data = _LIFE_PATH_DATA.get(life_path)
    if not data:
        # Fallback for 0 or unknown: reduce master to digit for lookup, or use default
        data = _LIFE_PATH_DATA.get(_reduce_to_digit_fallback(life_path)) if life_path else None
        if not data:
            data = _default_data(life_path)

    return {
        "lifePath": life_path,
        "traits": list(data.get("traits", [])),
        "strengths": list(data.get("strengths", [])),
        "challenges": list(data.get("challenges", [])),
    }


def _reduce_to_digit_fallback(n: int) -> int:
    """Force reduce to 1-9 for lookup when master number has no dedicated row."""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def _default_data(lp: int) -> dict[str, list[str]]:
    return {
        "traits": ["Reflective", "Individual"],
        "strengths": ["Unique path", "Potential for growth"],
        "challenges": ["Integration", "Balance"],
    }


# Life path 1–9, 11, 22, 33: traits, strengths, challenges
_LIFE_PATH_DATA: dict[int, dict[str, list[str]]] = {
    1: {
        "traits": ["Leader", "Initiative", "Confidence", "Ambition"],
        "strengths": ["Decisive", "Self-starter", "Visionary"],
        "challenges": ["Impatience", "Stubbornness", "Isolation"],
    },
    2: {
        "traits": ["Peacemaker", "Harmony", "Sensitivity", "Support"],
        "strengths": ["Diplomacy", "Teamwork", "Empathy"],
        "challenges": ["Overthinking", "People-pleasing", "Indecision"],
    },
    3: {
        "traits": ["Communicator", "Joy", "Creativity", "Expression"],
        "strengths": ["Optimism", "Storytelling", "Imagination"],
        "challenges": ["Scattered focus", "Mood swings", "Procrastination"],
    },
    4: {
        "traits": ["Builder", "Structure", "Practicality", "Dedication"],
        "strengths": ["Reliability", "Planning", "Hard work"],
        "challenges": ["Rigidity", "Workaholism", "Fear of change"],
    },
    5: {
        "traits": ["Adventurer", "Curiosity", "Versatility", "Freedom"],
        "strengths": ["Adaptability", "Courage", "Resourcefulness"],
        "challenges": ["Restlessness", "Impulsivity", "Commitment issues"],
    },
    6: {
        "traits": ["Nurturer", "Service", "Compassion", "Responsibility"],
        "strengths": ["Loyalty", "Healing", "Steadiness"],
        "challenges": ["Overgiving", "Perfectionism", "Self-sacrifice"],
    },
    7: {
        "traits": ["Seeker", "Analysis", "Spirituality", "Depth"],
        "strengths": ["Insight", "Research", "Intuition"],
        "challenges": ["Isolation", "Skepticism", "Aloofness"],
    },
    8: {
        "traits": ["Achiever", "Ambition", "Authority", "Success"],
        "strengths": ["Leadership", "Strategy", "Resilience"],
        "challenges": ["Control", "Materialism", "Workaholism"],
    },
    9: {
        "traits": ["Humanitarian", "Wisdom", "Generosity", "Idealism"],
        "strengths": ["Compassion", "Completion", "Global perspective"],
        "challenges": ["Emotional intensity", "Boundary issues", "Letting go"],
    },
    11: {
        "traits": ["Intuitive", "Inspiration", "Idealism", "Vision"],
        "strengths": ["Psychic sensitivity", "Inspiration", "Healing potential"],
        "challenges": ["Nervous energy", "Self-doubt", "Overwhelm"],
    },
    22: {
        "traits": ["Master Builder", "Practical vision", "Manifestation", "Large-scale impact"],
        "strengths": ["Turning dreams into reality", "Organization", "Influence"],
        "challenges": ["Pressure", "Perfectionism", "Burnout"],
    },
    33: {
        "traits": ["Master Teacher", "Compassion", "Healing", "Service"],
        "strengths": ["Selfless giving", "Spiritual teaching", "Nurturing"],
        "challenges": ["Martyrdom", "Overgiving", "Emotional burden"],
    },
}
