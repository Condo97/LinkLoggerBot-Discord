# models.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Link:
    link_id: int
    web_url: str
    summary: str
    creation_date: datetime
    is_active: bool = True