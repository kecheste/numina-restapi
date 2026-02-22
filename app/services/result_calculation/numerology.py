"""
Numerology: Life Path (from birth date) and Soul Urge (from name vowels).
Reduce-to-digit: sum digits until single digit (e.g. 11 -> 2, 22 -> 4).
"""

def reduce_to_digit(n: int) -> int:
    """Reduce n to a single digit by repeatedly summing digits. 0 stays 0."""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def compute_numerology(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    name: str,
) -> dict[str, int] | None:
    """
    Compute life_path (from birth date digits) and soul_urge (from vowels in name).
    Returns None if name is missing or empty after stripping.
    """
    # Life Path: all digits of date (YYYYMMDD) summed then reduced
    date_str = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"
    digits = [int(d) for d in date_str if d.isdigit()]
    if not digits:
        return None
    life_path = reduce_to_digit(sum(digits))

    # Soul Urge: vowels in name (A=1, B=2, ... Z=26), sum then reduce
    clean_name = (name or "").strip().upper()
    if not clean_name:
        return None
    vowels = "AEIOU"
    vowel_values = []
    for c in clean_name:
        if c in vowels and "A" <= c <= "Z":
            vowel_values.append(ord(c) - 64)  # A=1, Z=26
    if not vowel_values:
        return None
    soul_urge = reduce_to_digit(sum(vowel_values))

    return {"life_path": life_path, "soul_urge": soul_urge}
