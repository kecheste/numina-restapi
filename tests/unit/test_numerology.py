from app.services.result_calculation.numerology import compute_numerology

def test_compute_numerology():
    result = compute_numerology(
        birth_year=1990,
        birth_month=1,
        birth_day=1,
        name="John Doe"
    )
    assert result is not None
    # Life path: 1990-01-01 -> 21 -> 3
    # Birthday: 01 -> 1
    # First name "John" vowels: O (15 -> 6). Soul urge: 6
    # Full name "JOHN DOE" -> J(1) O(6) H(8) N(5) D(4) O(6) E(5) = sum 35 -> 8
    
    assert result["life_path"] == 3
    assert result["birth_day"] == 1
    assert result["soul_urge"] == 6
    assert result["expression_number"] == 8
