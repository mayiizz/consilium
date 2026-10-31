from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    workspace_id: str
    type: str
    title: str
    body: str = ""
    task_id: Optional[str] = None
    research_job_id: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse] = Field(default_factory=list)
    unread_count: int = 0
    total: int = 0


class CreateResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    constraints: str = Field(default="", max_length=2000)
    research_type: str = Field(
        default="general",
        description="student_project | academic | technical | competitor_analysis | general",
    )


class ResearchJobResponse(BaseModel):
    id: str
    workspace_id: str
    topic: str
    constraints: str = ""
    status: str
    document_id: Optional[str] = None
    error: Optional[str] = None
    sources_count: int = 0
    summary_preview: str = ""
    phase: str = "planning"
    research_type: str = "general"
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    visuals: List[Dict[str, Any]] = Field(default_factory=list)
    plan_notes: str = ""
    created_at: datetime
    updated_at: datetime


class ResearchJobListResponse(BaseModel):
    items: List[ResearchJobResponse] = Field(default_factory=list)
    total: int = 0
