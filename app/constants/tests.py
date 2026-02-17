"""Static test catalog (aligned with frontend allTests). Locked/premium handled by frontend."""

from typing import TypedDict


class TestItem(TypedDict):
    id: int
    title: str
    category: str
    category_id: str
    questions: int


TESTS: list[TestItem] = [
    {"id": 1, "title": "Astrology Chart", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 12},
    {"id": 2, "title": "Numerology", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 10},
    {"id": 3, "title": "Starseed origins", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 9},
    {"id": 4, "title": "Human Design", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 15},
    {"id": 5, "title": "Transits", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 15},
    {"id": 6, "title": "Zodiac Element & Modality", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 15},
    {"id": 7, "title": "MBTI Type", "category": "Psychological Profile", "category_id": "psychological", "questions": 16},
    {"id": 8, "title": "Shadow Work Lens", "category": "Psychological Profile", "category_id": "psychological", "questions": 20},
    {"id": 9, "title": "Big Five", "category": "Psychological Profile", "category_id": "psychological", "questions": 20},
    {"id": 10, "title": "Core Values Sort", "category": "Psychological Profile", "category_id": "psychological", "questions": 18},
    {"id": 11, "title": "Cognitive Style", "category": "Psychological Profile", "category_id": "psychological", "questions": 14},
    {"id": 12, "title": "Mind Mirror", "category": "Psychological Profile", "category_id": "psychological", "questions": 14},
    {"id": 13, "title": "Chakra Assessment Scan", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 8},
    {"id": 14, "title": "Energy Archetype", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 11},
    {"id": 15, "title": "Emotional Regulation Type", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 13},
    {"id": 16, "title": "Stress Balance Index", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 16},
    {"id": 17, "title": "Somatic Connection", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 16},
    {"id": 18, "title": "Energy Synthesis", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 16},
    {"id": 19, "title": "Life Path Number", "category": "Soul Path & Karma", "category_id": "soul", "questions": 10},
    {"id": 20, "title": "Soul Urge / Heart's Desire", "category": "Soul Path & Karma", "category_id": "soul", "questions": 15},
    {"id": 21, "title": "Past Life Vibes", "category": "Soul Path & Karma", "category_id": "soul", "questions": 17},
    {"id": 22, "title": "Karmic Lessons", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19},
    {"id": 23, "title": "Inner Child Dialogue", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19},
    {"id": 24, "title": "Soul Compass", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19},
]
