from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    email: str
    is_active: bool
    role: str
    created_at: datetime
    external_id: str | None = None
