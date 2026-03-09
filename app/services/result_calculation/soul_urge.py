"""
Soul Urge / Heart's Desire: computed from vowels in first name only (Pythagorean 1-9).
First name = first token of full name (e.g. "John" from "John Doe").
Sum vowel values (Pythagorean), reduce to 1–9 or keep 11, 22, 33.
Returns JSON: { soulUrge, traits[], strengths[], challenges[] }.
"""

from typing import Any

VOWELS = "AEIOU"
MASTER_NUMBERS = (11, 22, 33)


def _pythagorean_value(c: str) -> int:
    """Pythagorean: A=1..I=9, J=1..Z=8."""
    if not c or len(c) != 1:
        return 0
    u = c.upper()
    if not ("A" <= u <= "Z"):
        return 0
    n = ord(u) - 64
    return (n - 1) % 9 + 1


def _reduce_to_soul_urge(n: int) -> int:
    """Reduce to single digit, but keep 11, 22, 33 as master numbers."""
    while n > 9:
        if n in MASTER_NUMBERS:
            return n
        n = sum(int(d) for d in str(n))
    return n if n >= 1 else 0


def _first_name(full_name: str) -> str:
    """First token of name (e.g. 'John' from 'John Doe')."""
    return (full_name or "").strip().split()[0] if (full_name or "").strip() else ""


def compute_soul_urge(*, full_name: str) -> dict[str, Any] | None:
    """
    Compute Soul Urge from vowels in first name only (Pythagorean 1-9).
    full_name can be "John Doe" or "John Doe, Father Name"; only "John" is used.
    Returns dict with soulUrge (int), traits[], strengths[], challenges[].
    Returns None if name is empty after stripping.
    """
    first = _first_name(full_name).upper()
    if not first:
        return None
    vowel_sum = sum(_pythagorean_value(c) for c in first if c in VOWELS and "A" <= c <= "Z")
    if vowel_sum == 0:
        return None
    soul_urge = _reduce_to_soul_urge(vowel_sum)

    data = _SOUL_URGE_DATA.get(soul_urge)
    if not data:
        data = _fallback_data(soul_urge)

    return {
        "soulUrge": soul_urge,
        "traits": list(data.get("traits", [])),
        "strengths": list(data.get("strengths", [])),
        "challenges": list(data.get("challenges", [])),
    }


def _fallback_data(n: int) -> dict[str, list[str]]:
    while n > 9 and n not in MASTER_NUMBERS:
        n = sum(int(d) for d in str(n))
    return _SOUL_URGE_DATA.get(n, {
        "traits": ["Reflective", "Inner drive"],
        "strengths": ["Depth", "Potential"],
        "challenges": ["Expression", "Balance"],
    })


# Soul Urge 1–9, 11, 22, 33: traits, strengths, challenges (Heart's Desire meanings)
_SOUL_URGE_DATA: dict[int, dict[str, list[str]]] = {
    1: {
        "traits": ["Independence", "Leadership", "Originality"],
        "strengths": ["Initiative", "Courage", "Self-reliance"],
        "challenges": ["Dominance", "Impatience", "Isolation"],
    },
    2: {
        "traits": ["Cooperation", "Diplomacy", "Sensitivity"],
        "strengths": ["Partnership", "Peace", "Intuition"],
        "challenges": ["Over-dependence", "Indecision", "Avoiding conflict"],
    },
    3: {
        "traits": ["Creativity", "Joy", "Expression"],
        "strengths": ["Optimism", "Communication", "Artistic"],
        "challenges": ["Scattered energy", "Superficiality", "Moodiness"],
    },
    4: {
        "traits": ["Stability", "Order", "Dedication"],
        "strengths": ["Reliability", "Building", "Discipline"],
        "challenges": ["Rigidity", "Stubbornness", "Overwork"],
    },
    5: {
        "traits": ["Freedom", "Variety", "Curiosity"],
        "strengths": ["Adaptability", "Adventure", "Resourcefulness"],
        "challenges": ["Restlessness", "Impulsiveness", "Commitment fear"],
    },
    6: {
        "traits": ["Responsibility", "Nurturing", "Harmony"],
        "strengths": ["Service", "Love", "Balance"],
        "challenges": ["Meddling", "Worry", "Self-sacrifice"],
    },
    7: {
        "traits": ["Wisdom", "Spirituality", "Analysis"],
        "strengths": ["Insight", "Introspection", "Truth-seeking"],
        "challenges": ["Aloofness", "Skepticism", "Isolation"],
    },
    8: {
        "traits": ["Achievement", "Authority", "Abundance"],
        "strengths": ["Ambition", "Executive skill", "Manifestation"],
        "challenges": ["Materialism", "Control", "Workaholism"],
    },
    9: {
        "traits": ["Compassion", "Completion", "Universality"],
        "strengths": ["Generosity", "Idealism", "Letting go"],
        "challenges": ["Martyrdom", "Emotional overwhelm", "Boundaries"],
    },
    11: {
        "traits": ["Inspiration", "Idealism", "Intuition"],
        "strengths": ["Vision", "Inspiration", "Sensitivity"],
        "challenges": ["Nervous energy", "Self-doubt", "Overwhelm"],
    },
    22: {
        "traits": ["Master builder", "Practical vision", "Large-scale service"],
        "strengths": ["Manifestation", "Organization", "Impact"],
        "challenges": ["Pressure", "Perfectionism", "Burnout"],
    },
    33: {
        "traits": ["Healing", "Teaching", "Compassionate service"],
        "strengths": ["Selfless love", "Spiritual teaching", "Nurturing"],
        "challenges": ["Martyrdom", "Overgiving", "Emotional burden"],
    },
}
