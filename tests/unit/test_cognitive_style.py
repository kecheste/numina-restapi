from app.services.result_calculation.cognitive_style import compute_cognitive_style

def test_compute_cognitive_style():
    answers = [
        {"id": 1, "answer": "Analyze recent events to deduce the cause"}, # analytical
        {"id": 2, "answer": "Research facts and data first"}, # analytical
        {"id": 3, "answer": "Notice emotional tone and feelings"}, # empathic
        {"id": 4, "answer": "Suggest a workable compromise"}, # practical
        {"id": 5, "answer": "Strongly Agree"}, # analytical
        {"id": 6, "answer": "Disagree"}, # empathic
        {"id": 7, "answer": "Neutral"}, # practical
        {"id": 8, "answer": "Strongly Disagree"}, # observational
        {"id": 9, "answer": "Agree"}, # balanced
        {"id": 10, "answer": "Strongly Agree"}, # analytical
        {"id": 11, "answer": "Disagree"}, # empathic
        {"id": 12, "answer": "Agree"} # balanced
    ]
    
    result = compute_cognitive_style(answers)
    assert result is not None
    assert "primary_style" in result
    assert "secondary_style" in result
    assert "scores" in result
    assert result["primary_style"] == "analytical"
