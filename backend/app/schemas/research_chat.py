from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResearchChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ResearchChatJobSnapshot(BaseModel):
    id: str
    topic: str = ""
    status: str = "pending"
    phase: str = "planning"
    research_type: str = "general"
    sources_count: int = 0
    summary_preview: str = ""
    document_id: Optional[str] = None
    error: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)


class ResearchChatMessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    used_web: bool = False
    research_job_id: Optional[str] = None
    job: Optional[ResearchChatJobSnapshot] = None


class ResearchChatResponse(BaseModel):
    message: ResearchChatMessageResponse
    used_web: bool = False
    research_job_id: Optional[str] = None


class ResearchChatHistoryResponse(BaseModel):
    messages: List[ResearchChatMessageResponse] = Field(default_factory=list)
    total: int = 0
