from app.services.result_calculation.mbti import compute_mbti, compute_mbti_detailed

def test_compute_mbti():
    answers = [
        {"id": 1, "answer": "Option 1 (I)"},
        {"id": 2, "answer": "Option 2 (I)"},
        {"id": 3, "answer": "Option 3 (E)"},
        {"id": 4, "answer": "Option 4 (I)"},
        {"id": 5, "answer": "Option (N)"},
        {"id": 6, "answer": "Option (N)"},
        {"id": 7, "answer": "Option (N)"},
        {"id": 8, "answer": "Option (S)"},
        {"id": 9, "answer": "Option (T)"},
        {"id": 10, "answer": "Option (T)"},
        {"id": 11, "answer": "Option (T)"},
        {"id": 12, "answer": "Option (F)"},
        {"id": 13, "answer": "Option (J)"},
        {"id": 14, "answer": "Option (J)"},
        {"id": 15, "answer": "Option (J)"},
        {"id": 16, "answer": "Option (P)"},
    ]
    
    # INTJ configuration
    result = compute_mbti(answers)
    assert result == "INTJ"
    
    result_detailed = compute_mbti_detailed(answers)
    assert result_detailed["type"] == "INTJ"
    assert result_detailed["dimensions"]["I"] == 3
    assert result_detailed["dimensions"]["E"] == 1
    assert result_detailed["confidence"]["Introversion"] == 75
