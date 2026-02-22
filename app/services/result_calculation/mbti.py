"""
MBTI Type: direct mapping from 4 answers to I/E, N/S, F/T, J/P.
Each question's selected option contains the letter in parentheses (e.g. "Alone (I)").
"""

import re
from typing import Any

MBTI_QUESTION_ORDER = (1, 2, 3, 4)


def _letter_from_option(option_text: str) -> str | None:
    """Extract single letter in parentheses from option text, e.g. 'Alone (I)' -> 'I'."""
    if not option_text or not isinstance(option_text, str):
        return None
    match = re.search(r"\(([A-Za-z])\)", option_text.strip())
    return match.group(1).upper() if match else None


def compute_mbti(answers: list[Any] | dict[str, Any]) -> str | None:
    """
    Compute MBTI type from submitted answers.
    Answers can be list of {question_id, prompt, answer_type, answer} or legacy dict.
    Returns 4-letter type (e.g. 'INFJ') or None if any dimension is missing.
    """
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

    letters: list[str] = []
    for qid in MBTI_QUESTION_ORDER:
        option_text = by_id.get(qid)
        letter = _letter_from_option(option_text) if option_text else None
        if not letter:
            return None
        letters.append(letter)

    return "".join(letters)
