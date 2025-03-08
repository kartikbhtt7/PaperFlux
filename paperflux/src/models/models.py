from datetime import datetime
from typing import List, Dict, Optional


class Paper:
    def __init__(
        self,
        paper_id: str,
        title: str,
        authors: List[Dict],
        summary: str,
        published_at: str,
        explanation: Optional[str] = None,
        pdf_url: Optional[str] = None,
    ):
        self.paper_id = paper_id
        self.title = title
        self.authors = authors
        self.summary = summary
        self.published_at = published_at
        self.explanation = explanation
        self.pdf_url = pdf_url
        self.processed_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "published_at": self.published_at,
            "explanation": self.explanation,
            "pdf_url": self.pdf_url,
            "processed_at": self.processed_at,
        }
