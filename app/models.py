from dataclasses import dataclass
from typing import Optional

@dataclass
class ReleaseNoteEvent:
    service: str
    published_date: str
    raw_text: str
    source_url: str
    event_hash: str
    doc_links: str = ""
    id: Optional[int] = None
    rule_score: float = 0.0
    popularity_score: float = 0.0
    final_score: float = 0.0
    ai_processed: bool = False
    ai_relevance: str = ""
    ai_summary: str = ""
    category: str = ""
    published_week: str = ""