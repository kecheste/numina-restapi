from app.services.result_calculation.soul_compass import compute_soul_compass

def test_compute_soul_compass():
    # Misaligned state check
    result = compute_soul_compass(mind=40, heart=50, body=40, soul=50)
    assert result["alignment_score"] == 45
    assert result["alignment_state"] == "Misaligned"
    assert result["imbalance"] == 10
    
    # Aligned state check
    result2 = compute_soul_compass(mind=90, heart=90, body=85, soul=90)
    assert result2["alignment_score"] == 89
    assert result2["alignment_state"] == "Aligned"
    assert result2["imbalance"] == 5
