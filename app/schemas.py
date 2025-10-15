from typing import List, Optional
from pydantic import BaseModel, Field


class Comment(BaseModel):
    sender: str
    type: str
    content: str
    name: Optional[str] = None
    visibility: Optional[str] = None


class Ticket(BaseModel):
    ticket_number: int
    ticket_title: str
    ticket_priority: str
    ticket_labels: List[str]
    ticket_status: str
    ticket_description: str
    comments: List[Comment] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    problem: str
    resolution_summary: str
    result_and_key_points: str
