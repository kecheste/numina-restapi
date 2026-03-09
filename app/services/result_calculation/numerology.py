"""
Numerology: Life Path, Birthday, Soul Urge, Expression.
Rules:
- Life Path = sum all digits of full birth date, reduce to one digit (keep 11/22/33). Uses same logic as life_path_number module.
- Birthday Number = day of birth only, reduce (keep 11/22). Computed from birth_day; not stored on user.
- Soul Urge = sum of vowels in first name only (Pythagorean 1-9), then reduce (keep 11/22/33).
- Expression = sum of all letters in full name (Pythagorean 1-9), then reduce (keep 11/22/33).
"""

from app.services.result_calculation.life_path_number import compute_life_path_number

MASTER_NUMBERS = (11, 22, 33)


def _reduce(n: int, keep_master: bool = True) -> int:
    """Reduce to single digit; optionally keep 11, 22, 33."""
    while n > 9:
        if keep_master and n in MASTER_NUMBERS:
            return n
        n = sum(int(d) for d in str(n))
    return n if n >= 1 else 0


def _pythagorean_value(c: str) -> int:
    """Pythagorean numerology: A=1..I=9, J=1..R=9, S=1..Z=8. Non-letters return 0."""
    if not c or len(c) != 1:
        return 0
    u = c.upper()
    if not ("A" <= u <= "Z"):
        return 0
    n = ord(u) - 64
    return (n - 1) % 9 + 1


def _first_name(full_or_display_name: str) -> str:
    """First token of name (e.g. 'John' from 'John Doe' or 'John Doe, Father Name')."""
    return (full_or_display_name or "").strip().split()[0] if (full_or_display_name or "").strip() else ""


def compute_numerology(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    name: str,
) -> dict[str, int] | None:
    """
    Compute life_path, birthday_number, soul_urge, expression_number.
    - Life path: from life_path_number module (single source of truth).
    - Birthday: from birth_day only (not stored on user).
    - Soul urge: vowels in first name only (name may be "John Doe" or include father name).
    - Expression: all letters in full name (name = full_name or name from user).
    Returns None if name is missing or empty after stripping, or date invalid.
    """
    life_path_result = compute_life_path_number(
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
    )
    if not life_path_result:
        return None
    life_path = life_path_result["lifePath"]

    day_digits = [int(d) for d in str(birth_day) if d.isdigit()]
    birthday_number = _reduce(sum(day_digits), keep_master=True) if day_digits else 0

    full_name = (name or "").strip().upper()
    if not full_name:
        return None

    first_name = _first_name(name or "").upper()
    if not first_name:
        return None
    vowels = "AEIOU"
    vowel_sum = sum(_pythagorean_value(c) for c in first_name if c in vowels and "A" <= c <= "Z")
    if vowel_sum == 0:
        return None
    soul_urge = _reduce(vowel_sum, keep_master=True)

    letter_sum = sum(_pythagorean_value(c) for c in full_name if "A" <= c <= "Z")
    if letter_sum == 0:
        return None
    expression_number = _reduce(letter_sum, keep_master=True)

    return {
        "life_path": life_path,
        "soul_urge": soul_urge,
        "birthday_number": birthday_number,
        "expression_number": expression_number,
    }
