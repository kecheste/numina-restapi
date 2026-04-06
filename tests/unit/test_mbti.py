from app.services.result_calculation.mbti import compute_mbti, compute_mbti_detailed

def test_compute_mbti_full_consensus():
    # 3/0 split for all dimensions -> 100% confidence
    answers = [
        {"id": 1, "answer": "Quiet alone (I)"},
        {"id": 2, "answer": "Listen (I)"},
        {"id": 3, "answer": "Solitude (I)"},
        {"id": 4, "answer": "Concepts (N)"},
        {"id": 5, "answer": "Possible (N)"},
        {"id": 6, "answer": "Intuition (N)"},
        {"id": 7, "answer": "Empathy (F)"},
        {"id": 8, "answer": "Harmony (F)"},
        {"id": 9, "answer": "Story (F)"},
        {"id": 10, "answer": "Planned (J)"},
        {"id": 11, "answer": "Plan out (J)"},
        {"id": 12, "answer": "Wait plan (J)"},
    ]
    
    # INFJ configuration
    assert compute_mbti(answers) == "INFJ"
    
    result = compute_mbti_detailed(answers)
    assert result["type"] == "INFJ"
    assert result["total_questions"] == 12
    assert result["confidence"]["Introversion"] == 100
    assert result["confidence"]["Intuition"] == 100
    assert result["confidence"]["Feeling"] == 100
    assert result["confidence"]["Judging"] == 100

def test_compute_mbti_majority_vote():
    # 2/1 split for all dimensions -> 67% confidence
    answers = [
        {"id": 1, "answer": "Quiet alone (I)"},
        {"id": 2, "answer": "Listen (I)"},
        {"id": 3, "answer": "People (E)"},  # 2 I, 1 E -> I (67%)
        
        {"id": 4, "answer": "Concepts (N)"},
        {"id": 5, "answer": "Possible (N)"},
        {"id": 6, "answer": "Facts (S)"},    # 2 N, 1 S -> N (67%)
        
        {"id": 7, "answer": "Logic (T)"},
        {"id": 8, "answer": "Issues (T)"},
        {"id": 9, "answer": "Story (F)"},    # 2 T, 1 F -> T (67%)
        
        {"id": 10, "answer": "Planned (J)"},
        {"id": 11, "answer": "Plan out (J)"},
        {"id": 12, "answer": "Go flow (P)"}, # 2 J, 1 P -> J (67%)
    ]
    
    assert compute_mbti(answers) == "INTJ"
    
    result = compute_mbti_detailed(answers)
    assert result["type"] == "INTJ"
    assert result["confidence"]["Introversion"] == 67
    assert result["confidence"]["Intuition"] == 67
    assert result["confidence"]["Thinking"] == 67
    assert result["confidence"]["Judging"] == 67

def test_compute_mbti_tie_break():
    # Tie cases should favor the first letter of the pair in defined mapping (if x_votes >= y_votes)
    # Mapping is: (I,E), (N,S), (F,T), (J,P) for IDs 7-9 it's F vs T.
    # Note: I defined ID 7-9 as (F,T) in mbti.py.
    
    answers = [
        {"id": 1, "answer": "Quiet alone (I)"},
        {"id": 2, "answer": "Quiet alone (I)"},
        {"id": 3, "answer": "Quiet alone (I)"},
        {"id": 4, "answer": "Concepts (N)"},
        {"id": 5, "answer": "Concepts (N)"},
        {"id": 6, "answer": "Concepts (N)"},
        
        {"id": 7, "answer": "Logic (T)"},    # wait, Logic is second in (F, T)
        {"id": 8, "answer": "Harmony (F)"},  # 1 F, 1 T so far
        # If we have only 2 answers? No, we have 3.
        {"id": 9, "answer": "Logic (T)"},    # 1 F, 2 T -> T
        
        {"id": 10, "answer": "Planned (J)"},
        {"id": 11, "answer": "Planned (J)"},
        {"id": 12, "answer": "Planned (J)"},
    ]
    # (3I, 3N, 2T, 3J) -> INTJ
    assert compute_mbti(answers) == "INTJ"
