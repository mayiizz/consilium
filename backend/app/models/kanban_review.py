from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import AuditMixin


class KanbanTaskReviewQueue(Document, AuditMixin):
    workspace_id: PydanticObjectId
    meeting_id: Optional[PydanticObjectId] = None
    candidate: dict = Field(default_factory=dict)
    reason: str = "low_confidence"
    reviewed: bool = False

    class Settings:
        name = "kanban_task_review_queue"
