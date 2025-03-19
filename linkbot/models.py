# models.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Link:
    link_id: int
    web_url: str
    summary: str
    category: str
    creation_date: datetime
    deleted: bool = False