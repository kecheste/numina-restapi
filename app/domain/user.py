from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: int
    external_id: str
    email: str
    created_at: datetime
