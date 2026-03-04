"""Synthesis API schemas. Result shape matches strict LLM output (youAre, sureThings, etc.)."""

from typing import Any

from pydantic import BaseModel


class SynthesisResultResponse(BaseModel):
    """GET /synthesis: preview (3 tests) or full (6+ tests)."""

    type: str
    completed_count: int
    result: dict[str, Any]
