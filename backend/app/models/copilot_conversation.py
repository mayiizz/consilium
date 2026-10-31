from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import AuditMixin, utcnow


class CopilotRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CopilotFeedback(str, Enum):
    UP = "up"
    DOWN = "down"


class CopilotMessage(BaseModel):
    role: CopilotRole
    content: str
    timestamp: datetime = Field(default_factory=utcnow)
    feedback: Optional[CopilotFeedback] = None
    message_id: Optional[str] = None


class CopilotConversation(Document, AuditMixin):
    workspace_id: PydanticObjectId
    user_id: PydanticObjectId
    messages: List[CopilotMessage] = Field(default_factory=list)

    class Settings:
        name = "copilotConversations"
