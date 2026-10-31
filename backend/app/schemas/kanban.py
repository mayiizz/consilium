from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class KanbanReviewItemResponse(BaseModel):
    id: str
    meeting_id: Optional[str] = None
    candidate: dict = Field(default_factory=dict)
    reason: str
    created_at: Optional[datetime] = None


class KanbanReviewListResponse(BaseModel):
    items: List[KanbanReviewItemResponse]
    total: int


class KanbanReviewActionResponse(BaseModel):
    message: str
    task_id: Optional[str] = None
