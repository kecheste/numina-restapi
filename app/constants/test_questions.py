"""Questions for tests. Only free tests (1 Astrology, 7 MBTI, 13 Chakra) have questions defined here; premium tests can be added later."""

from typing import TypedDict


class QuestionOption(TypedDict, total=False):
    value: str
    label: str


class QuestionItem(TypedDict, total=False):
    id: int
    prompt: str
    answer_type: str  # text | date | time | single_choice | multiple_choice | slider
    options: list[str]
    slider_min: int
    slider_max: int
    required: bool


# test_id -> list of questions (order preserved)
TEST_QUESTIONS: dict[int, list[QuestionItem]] = {
    # 1. Astrology Chart (free) – birth data
    1: [
        {"id": 1, "prompt": "What is your full name?", "answer_type": "text", "required": True},
        {"id": 2, "prompt": "What is your date of birth?", "answer_type": "date", "required": True},
        {"id": 3, "prompt": "What is your time of birth? (24-hour, e.g. 17:00)", "answer_type": "time", "required": True},
        {"id": 4, "prompt": "Where were you born? (City, Country)", "answer_type": "text", "required": True},
    ],
    # 7. MBTI Type (free) – 4 preferences
    7: [
        {
            "id": 1,
            "prompt": "Do you gain energy from being alone or with others?",
            "answer_type": "single_choice",
            "options": ["Alone (I)", "With Others (E)"],
            "required": True,
        },
        {
            "id": 2,
            "prompt": "Do you focus more on ideas or on facts?",
            "answer_type": "single_choice",
            "options": ["Ideas (N)", "Facts (S)"],
            "required": True,
        },
        {
            "id": 3,
            "prompt": "When deciding, do you lean on feelings or logic?",
            "answer_type": "single_choice",
            "options": ["Feelings (F)", "Logic (T)"],
            "required": True,
        },
        {
            "id": 4,
            "prompt": "Do you prefer planning or spontaneity?",
            "answer_type": "single_choice",
            "options": ["Planned (J)", "Flexible (P)"],
            "required": True,
        },
    ],
    # 13. Chakra Alignment Scan (free) – 10 questions from PDF
    13: [
        {
            "id": 1,
            "prompt": "Rate your current overall energy level:",
            "answer_type": "slider",
            "slider_min": 0,
            "slider_max": 100,
            "required": True,
        },
        {
            "id": 2,
            "prompt": "Which color feels most aligned with how you feel right now?",
            "answer_type": "single_choice",
            "options": ["Red", "Orange", "Yellow", "Green", "Blue", "Indigo", "Violet", "White"],
            "required": True,
        },
        {
            "id": 3,
            "prompt": "Where in your body do you most often notice tension or discomfort?",
            "answer_type": "single_choice",
            "options": ["Root", "Sacral", "Solar Plexus", "Heart", "Throat", "Third Eye", "Crown"],
            "required": True,
        },
        {
            "id": 4,
            "prompt": "Which emotion do you experience most strongly today?",
            "answer_type": "multiple_choice",
            "options": [
                "Security/Anxiety",
                "Creativity/Pleasure",
                "Confidence/Self-Doubt",
                "Love/Vulnerability",
                "Communication/Blocks",
                "Clarity/Confusion",
                "Spiritual Connection/Escapism",
            ],
            "required": True,
        },
        {
            "id": 5,
            "prompt": "Select any physical symptoms you've noticed recently:",
            "answer_type": "multiple_choice",
            "options": [
                "Digestive Issues",
                "Neck/Throat Tightness",
                "Headaches",
                "Lower-Back Pain",
                "Chest Tightness",
                "Fatigue",
                "Over-thinking",
            ],
            "required": True,
        },
        {
            "id": 6,
            "prompt": "How strong is your sense of purpose or connection to the Divine?",
            "answer_type": "single_choice",
            "options": ["Very Strong", "Moderate", "Weak", "Uncertain"],
            "required": True,
        },
        {
            "id": 7,
            "prompt": "Do you have any regular grounding or energy-clearing practices?",
            "answer_type": "single_choice",
            "options": ["Yes", "No"],
            "required": True,
        },
        {
            "id": 8,
            "prompt": "When under stress, what's your instinctive response?",
            "answer_type": "single_choice",
            "options": ["Fight", "Flight", "Freeze", "Flow"],
            "required": True,
        },
        {
            "id": 9,
            "prompt": "How easy is it for you to speak your truth?",
            "answer_type": "single_choice",
            "options": ["Very Easy", "Sometimes Easy", "Often Difficult", "I Stay Silent"],
            "required": True,
        },
        {
            "id": 10,
            "prompt": "Do you experience vivid intuition, dreams, or sudden \"downloads\"?",
            "answer_type": "single_choice",
            "options": ["Frequently", "Occasionally", "Rarely", "Never"],
            "required": True,
        },
    ],
}
