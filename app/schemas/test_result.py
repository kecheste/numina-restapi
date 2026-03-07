"""Schemas for test results (frontend-aligned)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

AnswerType = Literal[
    "text", "date", "time", "single_choice", "multiple_choice", "slider", "color"
]

class ShowWhen(BaseModel):
    """Show this question only when another question's answer equals value."""

    question_id: int
    value: str


class QuestionOut(BaseModel):
    """Single question for GET /tests/{id_or_slug}/questions (frontend-aligned)."""

    id: int
    prompt: str
    answer_type: AnswerType
    options: list[str] | None = None
    slider_min: int = 0
    slider_max: int = 100
    required: bool = True
    options_from_question_id: int | None = None  # use that question's answer (list) as options
    show_when: ShowWhen | None = None  # only show when answer of question_id equals value
    max_selections: int | None = None  # for multiple_choice: allow at most this many


class ElementDistribution(BaseModel):
    fire: int = 0
    earth: int = 0
    air: int = 0
    water: int = 0


class AstrologyChartResponse(BaseModel):
    """Response for GET /tests/astrology-chart (computed from user birth data)."""

    sun_sign: str
    moon_sign: str
    rising_sign: str
    element_distribution: ElementDistribution


class NumerologyResponse(BaseModel):
    """Response for GET /tests/numerology (computed from user birth date and name)."""

    life_path: int
    soul_urge: int


class AstrologyBlueprintResponse(BaseModel):
    """AI-generated copy for onboarding astrology blueprint screen."""

    sun_description: str
    moon_description: str
    rising_description: str
    cosmic_traits_summary: str


class AstrologyChartNarrativeOverlap(BaseModel):
    label: str
    description: str


class AstrologyChartNarrativeResponse(BaseModel):
    """AI-generated full narrative for Astrology Chart result view."""

    title: str
    core_traits: list[str]
    narrative: str
    strengths: list[str]
    challenges: list[str]
    avoid_this: list[str]
    overlaps: list[AstrologyChartNarrativeOverlap]
    try_this: list[str]
    spiritual_insight: str


class NumerologyBlueprintItem(BaseModel):
    number: str
    title: str
    description: str


class NumerologyBlueprintResponse(BaseModel):
    """AI-generated copy for onboarding numerology blueprint screen."""

    items: list[NumerologyBlueprintItem]


class EnergySynthesisResponse(BaseModel):
    """Response for GET /tests/energy-synthesis (computed from primary axis + heart status)."""

    fusion: str  # "Clarity" or "Integration"
    avg: float


class LifePathNumberResponse(BaseModel):
    """Life Path Number: computed from date of birth. Output: lifePath, traits, strengths, challenges."""

    lifePath: int
    traits: list[str]
    strengths: list[str]
    challenges: list[str]


class SoulUrgeResponse(BaseModel):
    """Soul Urge / Heart's Desire: computed from vowels in full name (Pythagorean). Same structure."""

    soulUrge: int
    traits: list[str]
    strengths: list[str]
    challenges: list[str]


class SoulCompassResponse(BaseModel):
    """Soul Compass: synthesis from values, motivations, fears, long-term desires."""

    coreDrive: str
    directionTheme: str
    growthFocus: str
    shadowPattern: str


class TestListItem(BaseModel):
    """Single test in GET /tests list (frontend-aligned). id is 1–24; slug is unique for URLs/fetching."""

    id: int
    slug: str
    title: str
    category: str
    category_id: str
    questions: int
    premium: bool
    auto_generated: bool
    already_taken: bool


class TestsListResponse(BaseModel):
    """Response for GET /tests (frontend-aligned)."""

    user_is_premium: bool
    tests: list[TestListItem]


class QuestionAnswerItem(BaseModel):
    """One question with its answer (for submit and stored result)."""

    question_id: int
    prompt: str
    answer_type: str | None = None
    answer: Any


class TestResultResponse(BaseModel):
    """Single test result as returned to frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_id: int
    test_title: str
    category: str
    completed_at: datetime
    answers: list[QuestionAnswerItem] | dict[str, Any]  # list preferred; legacy dict allowed
    status: str
    score: float | None
    personality_type: str | None
    insights: list[str] | None
    recommendations: list[str] | None
    narrative: str | None = None  # LLM-generated prose from computed result
    extracted_json: dict[str, Any] | list[Any] | None = None  # compact JSON; narrative uses only this for text tests
    llm_result_json: dict[str, Any] | None = None  # structured LLM output: title, summary, insights, recommendations, takeaway


class SubmitTestRequest(BaseModel):
    """Body for POST /tests/submit."""

    test_id: int
    test_title: str
    category: str
    answers: list[QuestionAnswerItem]


class SubmitTestResponse(BaseModel):
    """Response after submitting a test: poll GET /tests/results/{id} for completion."""

    result_id: int
    status: str = "pending_ai"
    message: str = "Result is being refined. Poll GET /tests/results/{result_id} for the completed result."
