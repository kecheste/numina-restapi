from app.services.result_calculation.emotional_regulation import compute_emotional_regulation

def test_compute_emotional_regulation():
    answers = [
        {"id": 1, "answer": "Strongly Agree"},
        {"id": 2, "answer": "Strongly Disagree"},
        {"id": 3, "answer": "Neutral"},
        {"id": 4, "answer": "Disagree"},
        {"id": 5, "answer": "Agree"},
        {"id": 6, "answer": "Neutral"},
        {"id": 7, "answer": "Disagree"},
        {"id": 8, "answer": "Strongly Agree"},
        {"id": 9, "answer": "Neutral"},
        {"id": 10, "answer": "Strongly Disagree"},
        {"id": 11, "answer": "Agree"},
        {"id": 12, "answer": "Strongly Agree"}
    ]
    # Quiet containment (1, 8, 12) all match "Strongly Agree" (avg 5.0 -> 100%)
    
    result = compute_emotional_regulation(answers)
    assert result is not None
    assert "primary_type" in result
    assert "scores" in result
    assert result["primary_type"] == "containment"
    assert result["scores"]["containment"] == 100
