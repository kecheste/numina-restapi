"""Daily message response (static, no LLM)."""

from pydantic import BaseModel


class DailyMessageResponse(BaseModel):
    message: str
    quote: str
