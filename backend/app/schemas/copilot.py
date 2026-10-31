from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1)
    meeting_id: Optional[str] = None


class CopilotCitation(BaseModel):
    source: str
    text: str
    confidence: Optional[float] = None
    network: Optional[str] = None
    uncertainty_band: Optional[str] = None


class CopilotMessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    citations: List[CopilotCitation] = Field(default_factory=list)
    timestamp: datetime
    kanban_refresh: Optional[dict] = None


class CopilotFeedbackRequest(BaseModel):
    workspace_id: str
    message_id: str
    feedback: str  # up | down


class CopilotHistoryResponse(BaseModel):
    messages: List[CopilotMessageResponse]
    total: int
