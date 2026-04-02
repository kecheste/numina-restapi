from app.services.result_calculation.shadow_work import compute_shadow_work

def test_compute_shadow_work():
    answers = [
        {"id": 1, "answer": "strongly agree"},
        {"id": 2, "answer": "disagree"},
        {"id": 3, "answer": "neutral"},
        {"id": 4, "answer": "strongly agree"},
        {"id": 5, "answer": "neutral"},
        {"id": 6, "answer": "strongly agree"},
        {"id": 7, "answer": "agree"},
        {"id": 8, "answer": "I feel stressed"},
        {"id": 9, "answer": "Very critical"},
        {"id": 10, "answer": "Rarely"}
    ]
    
    # suppressed_expression from q1, q4, q6 -> strongly agree -> 5 -> 100%
    result = compute_shadow_work(answers)
    
    assert result is not None
    assert "primary_shadow" in result
    assert result["primary_shadow"] == "suppressed_expression"
    assert result["scores"]["suppressed_expression"] == 100
    assert result["emotion_coping"] == "I feel stressed"
