"""Test catalog: source of truth for Explore cards. Frontend fetches via GET /tests (auth required) for list + user context."""

from typing import TypedDict


class TestItem(TypedDict):
    id: int
    title: str
    category: str
    category_id: str
    questions: int
    auto_generated: bool
    premium: bool


TESTS: list[TestItem] = [
    # Cosmic Identity (1–6)
    {"id": 1, "title": "Astrology Chart", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 4, "auto_generated": False, "premium": False},
    {"id": 2, "title": "Numerology", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "auto_generated": True, "premium": True},
    {"id": 3, "title": "Starseed Origins", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 9, "auto_generated": False, "premium": True},
    {"id": 4, "title": "Human Design", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "auto_generated": True, "premium": True},
    {"id": 5, "title": "Transits", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "auto_generated": True, "premium": True},
    {"id": 6, "title": "Zodiac Element and Modality", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "auto_generated": True, "premium": True},
    # Psychological Profile (7–12)
    {"id": 7, "title": "MBTI Type", "category": "Psychological Profile", "category_id": "psychological", "questions": 4, "auto_generated": False, "premium": False},
    {"id": 8, "title": "Shadow Work Lens", "category": "Psychological Profile", "category_id": "psychological", "questions": 20, "auto_generated": False, "premium": True},
    {"id": 9, "title": "Big Five", "category": "Psychological Profile", "category_id": "psychological", "questions": 15, "auto_generated": False, "premium": True},
    {"id": 10, "title": "Core Values Sort", "category": "Psychological Profile", "category_id": "psychological", "questions": 18, "auto_generated": False, "premium": True},
    {"id": 11, "title": "Cognitive Style", "category": "Psychological Profile", "category_id": "psychological", "questions": 14, "auto_generated": False, "premium": True},
    {"id": 12, "title": "Mind Mirror", "category": "Psychological Profile", "category_id": "psychological", "questions": 14, "auto_generated": False, "premium": True},
    # Energy and Wellbeing (13–18)
    {"id": 13, "title": "Chakra Alignment Scan", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 10, "auto_generated": False, "premium": False},
    {"id": 14, "title": "Energy Archetype", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 11, "auto_generated": False, "premium": True},
    {"id": 15, "title": "Emotional Regulation Type", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 13, "auto_generated": False, "premium": True},
    {"id": 16, "title": "Stress Balance Index", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 16, "auto_generated": False, "premium": True},
    {"id": 17, "title": "Somatic Connection", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 16, "auto_generated": False, "premium": True},
    {"id": 18, "title": "Energy Synthesis", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 0, "auto_generated": True, "premium": True},
    # Soul Path and Karma (19–24)
    {"id": 19, "title": "Life Path Number", "category": "Soul Path & Karma", "category_id": "soul", "questions": 0, "auto_generated": True, "premium": True},
    {"id": 20, "title": "Soul Urge / Heart's Desire", "category": "Soul Path & Karma", "category_id": "soul", "questions": 0, "auto_generated": True, "premium": True},
    {"id": 21, "title": "Past Life Vibes", "category": "Soul Path & Karma", "category_id": "soul", "questions": 17, "auto_generated": False, "premium": True},
    {"id": 22, "title": "Karmic Lessons", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19, "auto_generated": False, "premium": True},
    {"id": 23, "title": "Inner Child Dialogue", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19, "auto_generated": False, "premium": True},
    {"id": 24, "title": "Soul Compass", "category": "Soul Path & Karma", "category_id": "soul", "questions": 0, "auto_generated": False, "premium": True},
]
