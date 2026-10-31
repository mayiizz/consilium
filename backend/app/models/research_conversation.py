from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import AuditMixin, utcnow


class ResearchChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ResearchChatMessage(BaseModel):
    role: ResearchChatRole
    content: str
    timestamp: datetime = Field(default_factory=utcnow)
    message_id: Optional[str] = None
    research_job_id: Optional[str] = None
    used_web: bool = False


class ResearchConversation(Document, AuditMixin):
    workspace_id: PydanticObjectId
    user_id: PydanticObjectId
    messages: List[ResearchChatMessage] = Field(default_factory=list)

    class Settings:
        name = "researchConversations"
        indexes = [[("workspace_id", 1), ("user_id", 1)]]
