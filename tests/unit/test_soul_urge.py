from app.services.result_calculation.soul_urge import compute_soul_urge

def test_compute_soul_urge():
    result = compute_soul_urge(full_name="John Doe")
    assert result is not None
    assert result["soulUrge"] == 6 # John -> O -> 15 -> 6
    assert isinstance(result["traits"], list)
    
    compute_soul_urge(full_name="Janea") # A(1)+E(5)+A(1) = 7. Let's make an 11: A(1)+U(3)+A(1)+O(6) -> A U A O
    # Let's just do a specific combination
    # "Auoo" -> A(1) U(3) O(6) O(6) = 16 -> 7
    result2 = compute_soul_urge(full_name="Alex J") # A(1) E(5) = 6
    assert result2 is not None
    assert result2["soulUrge"] == 6
