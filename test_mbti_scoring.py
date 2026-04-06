import sys
import os

# Add backend to path
project_root = r'c:\Users\kecheste\Documents\projects\numina\backend'
sys.path.append(project_root)

# Set environment variables if needed
os.environ["PYTHONPATH"] = project_root

from app.services.result_calculation.mbti import compute_mbti_detailed

# Mock answers for INTJ
# 1 (I), 2 (I), 3 (I) -> I 100%
# 4 (N), 5 (N), 6 (N) -> N 100%
# 7 (F), 8 (T), 9 (T) -> T 67%
# 10 (J), 11 (J), 12 (P) -> J 67%
# Expected: INTJ, I:100, N:100, T:67, J:67

answers = [
    {"id": 1, "answer": "Spending quiet time alone (I)"},
    {"id": 2, "answer": "Listen more and speak selectively (I)"},
    {"id": 3, "answer": "Recharge in solitude (I)"},
    {"id": 4, "answer": "Concepts and possibilities (N)"},
    {"id": 5, "answer": "What could be possible (N)"},
    {"id": 6, "answer": "Patterns and intuition (N)"},
    {"id": 7, "answer": "Personal values and empathy (F)"},
    {"id": 8, "answer": "Resolving the issue fairly and accurately (T)"},
    {"id": 9, "answer": "A strong logical argument or proof (T)"},
    {"id": 10, "answer": "Your schedule is planned and decided (J)"},
    {"id": 11, "answer": "Plan it out and follow steps (J)"},
    {"id": 12, "answer": "Adapt easily and go with the flow (P)"},
]

try:
    res = compute_mbti_detailed(answers)
    print(f"Type: {res['type']}")
    print(f"Confidence: {res['confidence']}")
    print(f"Total Questions: {res['total_questions']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
