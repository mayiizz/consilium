from datetime import datetime
from typing import Any, Dict, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.models.base import utcnow


class GitHubWebhookEvent(Document):
    workspace_id: PydanticObjectId
    event_type: str
    delivery_id: Indexed(str, unique=True)
    payload: Dict[str, Any] = Field(default_factory=dict)
    task_key: Optional[str] = None
    task_id: Optional[PydanticObjectId] = None
    processed: bool = False
    processed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "githubWebhookEvents"
