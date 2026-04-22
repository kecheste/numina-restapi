"""
MBTI Type: deterministic majority-vote scoring from 12 questions (3 per dimension).

Questions 1-3:  I / E  (Introversion vs Extraversion)
Questions 4-6:  N / S  (Intuition vs Sensing)
Questions 7-9:  F / T  (Feeling vs Thinking)
Questions 10-12: J / P (Judging vs Perceiving)

Each option text carries its letter in parentheses (e.g. "Spending quiet time alone (I)").
The letter with most votes per dimension wins; ties default to the first of the pair.

`compute_mbti_detailed` – returns type, raw vote counts, and confidence percentages.
`compute_mbti`          – thin wrapper that returns only the 4-letter type string (backward compat).
"""

import re
from typing import Any

_QUESTION_DIMENSION: dict[int, tuple[str, str]] = {
    1: ("I", "E"), 2: ("I", "E"), 3: ("I", "E"),
    4: ("N", "S"), 5: ("N", "S"), 6: ("N", "S"),
    7: ("F", "T"), 8: ("F", "T"), 9: ("F", "T"),
    10: ("J", "P"), 11: ("J", "P"), 12: ("J", "P"),
}

_DIMENSION_GROUPS: list[tuple[str, str, list[int]]] = [
    ("I", "E", [1, 2, 3]),
    ("N", "S", [4, 5, 6]),
    ("F", "T", [7, 8, 9]),
    ("J", "P", [10, 11, 12]),
]

_OPTION_TO_LETTER: dict[int, dict[str, str]] = {
    1: {"Spending quiet time alone": "I", "Being around people or social activity": "E"},
    2: {"Listen more and speak selectively": "I", "Speak easily and engage actively": "E"},
    3: {"Recharge in solitude": "I", "Do something with others": "E"},
    4: {"Concepts and possibilities": "N", "Practical details and facts": "S"},
    5: {"What could be possible": "N", "What is realistically likely": "S"},
    6: {"Patterns and intuition": "N", "Experience and observable facts": "S"},
    7: {"Personal values and empathy": "F", "Logic and objective analysis": "T"},
    8: {"Maintaining harmony and understanding": "F", "Resolving the issue fairly and accurately": "T"},
    9: {"A person's individual story or circumstances": "F", "A strong logical argument or proof": "T"},
    10: {"Your schedule is planned and decided": "J", "Your schedule is open and flexible": "P"},
    11: {"Plan it out and follow steps": "J", "Dive in and adapt as you go": "P"},
    12: {"Feel slightly stressed and want a new plan": "J", "Adapt easily and go with the flow": "P"},
}


def _letter_from_option(option_text: str, question_id: int | None = None) -> str | None:
    """
    Extract single letter in parentheses from option text, e.g. 'Alone (I)' -> 'I'.
    If no letter is found, fall back to the _OPTION_TO_LETTER map.
    """
    if not option_text or not isinstance(option_text, str):
        return None
    
    match = re.search(r"\(([A-Za-z])\)", option_text.strip())
    if match:
        return match.group(1).upper()
    
    if question_id in _OPTION_TO_LETTER:
        return _OPTION_TO_LETTER[question_id].get(option_text.strip())
    
    return None


def _parse_answers(answers: list[Any] | dict[str, Any]) -> dict[int, str]:
    """Return {question_id: option_text} from any answer format."""
    by_id: dict[int, str] = {}
    if isinstance(answers, list):
        for item in answers:
            d = item if isinstance(item, dict) else {}
            qid = d.get("id") or d.get("question_id") or getattr(item, "question_id", None)
            ans = d.get("answer") or getattr(item, "answer", None)
            if qid is not None and ans is not None:
                if isinstance(ans, list):
                    ans = ans[0] if ans else ""
                by_id[int(qid)] = str(ans).strip()
    else:
        for qid, ans in (answers or {}).items():
            try:
                k = int(qid)
            except (TypeError, ValueError):
                continue
            if isinstance(ans, list):
                ans = ans[0] if ans else ""
            by_id[k] = str(ans).strip()
    return by_id


def compute_mbti_detailed(
    answers: list[Any] | dict[str, Any],
) -> dict[str, Any]:
    """
    Deterministically compute MBTI type + per-dimension breakdown using 16 questions.
    Logic follows user specification:
    - Type winner: x >= y ? X : Y
    - Pair percentage: round(max(x,y) / total * 100)
    """
    _LABEL = {
        "I": "Introversion", "E": "Extraversion",
        "N": "Intuition", "S": "Sensing",
        "T": "Thinking", "F": "Feeling",
        "J": "Judging", "P": "Perceiving"
    }

    by_id = _parse_answers(answers)
    type_letters: list[str] = []
    dimensions: dict[str, int] = {}
    confidence: dict[str, int] = {}

    for first, second, question_ids in _DIMENSION_GROUPS:
        x_votes = 0
        y_votes = 0
        for qid in question_ids:
            option_text = by_id.get(qid)
            if option_text:
                letter = _letter_from_option(option_text, qid)
                if letter == first:
                    x_votes += 1
                elif letter == second:
                    y_votes += 1

        dimensions[first] = x_votes
        dimensions[second] = y_votes

        winner = first if x_votes >= y_votes else second
        type_letters.append(winner)

        total = x_votes + y_votes
        if total == 0:
            percentage = 50
        else:
            percentage = round((max(x_votes, y_votes) / total) * 100)
        
        confidence[_LABEL[winner]] = percentage

    return {
        "type": "".join(type_letters),
        "dimensions": dimensions,
        "confidence": confidence,
        "total_questions": 12,
    }


def compute_mbti(answers: list[Any] | dict[str, Any]) -> str | None:
    """Backward-compatible wrapper: returns 4-letter type or None."""
    result = compute_mbti_detailed(answers)
    t = result.get("type", "")
    return t if len(t) == 4 else None
