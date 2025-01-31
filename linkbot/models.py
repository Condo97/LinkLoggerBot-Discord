from dataclasses import dataclass
from typing import List, Optional, TypedDict

@dataclass
class Link:
    link_id: int
    web_url: str
    summary: str
    creation_date: str
    is_active: bool = True

class ChatClassification(TypedDict):
    command: str
    link_query_days_ago_limit: Optional[int]
    link_query_count_limit: Optional[int]
    needs_scraping: List[int]  # List of link_ids needing scraping

class ChatCommand:
    def __init__(self, classification: ChatClassification):
        self.command = classification['command']
        self.link_query_days_ago_limit = classification.get('link_query_days_ago_limit')
        self.link_query_count_limit = classification.get('link_query_count_limit')
        self.needs_scraping = classification.get('needs_scraping', [])