from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    id: int
    created_at: datetime
    delivered_at: Optional[datetime]
    total_cents: int
