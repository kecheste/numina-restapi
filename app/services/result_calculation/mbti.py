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
from collections import Counter
from typing import Any

_QUESTION_DIMENSION: dict[int, tuple[str, str]] = {
    1: ("I", "E"),
    2: ("I", "E"),
    3: ("I", "E"),
    4: ("N", "S"),
    5: ("N", "S"),
    6: ("N", "S"),
    7: ("F", "T"),
    8: ("F", "T"),
    9: ("F", "T"),
    10: ("J", "P"),
    11: ("J", "P"),
    12: ("J", "P"),
}

_DIMENSION_GROUPS: list[tuple[str, str, list[int]]] = [
    ("I", "E", [1, 2, 3]),
    ("N", "S", [4, 5, 6]),
    ("F", "T", [7, 8, 9]),
    ("J", "P", [10, 11, 12]),
]


def _letter_from_option(option_text: str) -> str | None:
    """Extract single letter in parentheses from option text, e.g. 'Alone (I)' -> 'I'."""
    if not option_text or not isinstance(option_text, str):
        return None
    match = re.search(r"\(([A-Za-z])\)", option_text.strip())
    return match.group(1).upper() if match else None


def _parse_answers(answers: list[Any] | dict[str, Any]) -> dict[int, str]:
    """Return {question_id: option_text} from any answer format."""
    by_id: dict[int, str] = {}
    if isinstance(answers, list):
        for item in answers:
            d = item if isinstance(item, dict) else {}
            qid = d.get("question_id") or getattr(item, "question_id", None)
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
    Deterministically compute MBTI type + per-dimension breakdown.

    Returns:
      {
        "type": "INFJ",
        "dimensions": {
          "I": 3, "E": 0,
          "N": 2, "S": 1,
          "F": 3, "T": 0,
          "J": 2, "P": 1,
        },
        "confidence": {
          "Introversion": 100,   # percentage of votes
          "Intuition": 67,
          "Feeling": 100,
          "Judging": 67,
        },
        "total_questions": 12,
      }
    """
    _LABEL = {
        "I": "Introversion", "E": "Extraversion",
        "N": "Intuition", "S": "Sensing",
        "F": "Feeling", "T": "Thinking",
        "J": "Judging", "P": "Perceiving"
    }

    by_id = _parse_answers(answers)
    type_letters: list[str] = []
    dimensions: dict[str, int] = {}
    confidence: dict[str, int] = {}

    for first, second, question_ids in _DIMENSION_GROUPS:
        votes: Counter = Counter()
        for qid in question_ids:
            option_text = by_id.get(qid)
            if option_text:
                letter = _letter_from_option(option_text)
                if letter in (first, second):
                    votes[letter] += 1

        total = sum(votes.values())
        for letter in (first, second):
            dimensions[letter] = votes.get(letter, 0)

        if not votes:
            winner = first
        else:
            winner = votes.most_common(1)[0][0]
            if winner not in (first, second):
                winner = first

        type_letters.append(winner)

        # Confidence = winning letter votes / total questions in dimension
        q_count = len(question_ids)
        winning_votes = dimensions[winner]
        confidence[_LABEL[winner]] = round(winning_votes / q_count * 100) if q_count else 0

    return {
        "type": "".join(type_letters),
        "dimensions": dimensions,
        "confidence": confidence,
        "total_questions": max(len(question_ids) * 4, 12),
    }


def compute_mbti(answers: list[Any] | dict[str, Any]) -> str | None:
    """Backward-compatible wrapper: returns 4-letter type or None."""
    result = compute_mbti_detailed(answers)
    t = result.get("type", "")
    return t if len(t) == 4 else None
