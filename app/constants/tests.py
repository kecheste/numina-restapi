"""Static test catalog (aligned with frontend allTests). Locked/premium handled by frontend.

auto_generated: True means the user does not take a separate test; the result is derived
from data they already provided (e.g. birth date/place). It does not mean the backend
generates the result automatically.
"""

from typing import TypedDict

class TestItem(TypedDict):
    id: int
    slug: str
    title: str
    category: str
    category_id: str
    questions: int
    premium: bool
    auto_generated: bool

TESTS: list[TestItem] = [
    {"id": 1, "slug": "astrology-chart", "title": "Astrology Chart", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "premium": False, "auto_generated": True},
    {"id": 7, "slug": "mbti-type", "title": "MBTI Type", "category": "Psychological Profile", "category_id": "psychological", "questions": 12, "premium": False, "auto_generated": False},
    {"id": 13, "slug": "chakra-assessment-scan", "title": "Chakra Assessment Scan", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 10, "premium": False, "auto_generated": False},
    {"id": 19, "slug": "life-path-number", "title": "Life Path Number", "category": "Soul Path & Karma", "category_id": "soul", "questions": 0, "premium": False, "auto_generated": True},
    {"id": 2, "slug": "numerology", "title": "Numerology", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "premium": True, "auto_generated": False},
    {"id": 3, "slug": "starseed-origins", "title": "Starseed origins", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 4, "slug": "human-design", "title": "Human Design", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "premium": True, "auto_generated": True},
    {"id": 5, "slug": "transits", "title": "Transits", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "premium": True, "auto_generated": False},
    {"id": 6, "slug": "zodiac-element-modality", "title": "Zodiac Element & Modality", "category": "Cosmic Identity", "category_id": "cosmic", "questions": 0, "premium": True, "auto_generated": False},
    {"id": 8, "slug": "shadow-work-lens", "title": "Shadow Work Lens", "category": "Psychological Profile", "category_id": "psychological", "questions": 10, "premium": True, "auto_generated": False},
    {"id": 9, "slug": "big-five", "title": "Big Five", "category": "Psychological Profile", "category_id": "psychological", "questions": 20, "premium": True, "auto_generated": False},
    {"id": 10, "slug": "core-values-sort", "title": "Core Values Sort", "category": "Psychological Profile", "category_id": "psychological", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 11, "slug": "cognitive-style", "title": "Cognitive Style", "category": "Psychological Profile", "category_id": "psychological", "questions": 6, "premium": True, "auto_generated": False},
    {"id": 12, "slug": "mind-mirror", "title": "Mind Mirror", "category": "Psychological Profile", "category_id": "psychological", "questions": 5, "premium": True, "auto_generated": False},
    {"id": 14, "slug": "energy-archetype", "title": "Energy Archetype", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 15, "slug": "emotional-regulation-type", "title": "Emotional Regulation Type", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 16, "slug": "stress-balance-index", "title": "Stress Balance Index", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 17, "slug": "somatic-connection", "title": "Somatic Connection", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 18, "slug": "energy-synthesis", "title": "Energy Synthesis", "category": "Energy & Wellbeing", "category_id": "energy", "questions": 0, "premium": True, "auto_generated": True},
    {"id": 20, "slug": "soul-urge-hearts-desire", "title": "Soul Urge / Heart's Desire", "category": "Soul Path & Karma", "category_id": "soul", "questions": 0, "premium": True, "auto_generated": True},
    {"id": 21, "slug": "past-life-vibes", "title": "Past Life Vibes", "category": "Soul Path & Karma", "category_id": "soul", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 22, "slug": "karmic-lessons", "title": "Karmic Lessons", "category": "Soul Path & Karma", "category_id": "soul", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 23, "slug": "inner-child-dialogue", "title": "Inner Child Dialogue", "category": "Soul Path & Karma", "category_id": "soul", "questions": 12, "premium": True, "auto_generated": False},
    {"id": 24, "slug": "soul-compass", "title": "Soul Compass", "category": "Soul Path & Karma", "category_id": "soul", "questions": 19, "premium": True, "auto_generated": False},
]

TESTS_BY_SLUG: dict[str, int] = {t["slug"]: t["id"] for t in TESTS}

def get_test_id(id_or_slug: int | str) -> int | None:
    """Return numeric test id from id or slug. None if not found."""
    if isinstance(id_or_slug, int):
        return id_or_slug if any(t["id"] == id_or_slug for t in TESTS) else None
    try:
        as_int = int(id_or_slug)
        return as_int if any(t["id"] == as_int for t in TESTS) else None
    except (TypeError, ValueError):
        pass
    return TESTS_BY_SLUG.get(id_or_slug)
