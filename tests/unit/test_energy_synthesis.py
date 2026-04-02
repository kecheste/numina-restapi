from app.services.result_calculation.energy_synthesis import compute_energy_synthesis

def test_compute_energy_synthesis():
    answers = [
        {"id": 3, "answer": "Strongly Agree"},
        {"id": 4, "answer": "Disagree"},
        {"id": 5, "answer": "Strongly Disagree"}, # heart_led
        {"id": 6, "answer": "Strongly Agree"},    # mind_led pt 1
        {"id": 7, "answer": "Strongly Agree"},
        {"id": 8, "answer": "Disagree"},
        {"id": 9, "answer": "Neutral"},
        {"id": 10, "answer": "Neutral"},
        {"id": 11, "answer": "Strongly Agree"},    # mind_led pt 2
        {"id": 12, "answer": "Neutral"}
    ]
    
    # mind_led -> avg(q6, q11) -> avg(5, 5) -> 5.0 -> 100%
    result = compute_energy_synthesis(answers)
    assert result is not None
    assert "primary_type" in result
    assert "scores" in result
    assert result["primary_type"] == "mind_led"
    assert result["scores"]["mind_led"] == 100
