from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.models.base import AuditMixin, utcnow


class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    DUE_SOON = "due_soon"
    RESEARCH_DONE = "research_done"


class Notification(Document, AuditMixin):
    user_id: Indexed(PydanticObjectId)
    workspace_id: PydanticObjectId
    type: NotificationType
    title: str
    body: str = ""
    task_id: Optional[PydanticObjectId] = None
    research_job_id: Optional[PydanticObjectId] = None
    dedupe_key: Indexed(str)
    read_at: Optional[datetime] = None

    class Settings:
        name = "notifications"
        indexes = [
            [("user_id", 1), ("read_at", 1), ("created_at", -1)],
            [("dedupe_key", 1)],
        ]


class ResearchJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ResearchJob(Document, AuditMixin):
    workspace_id: Indexed(PydanticObjectId)
    topic: str
    constraints: str = ""
    status: ResearchJobStatus = ResearchJobStatus.PENDING
    document_id: Optional[PydanticObjectId] = None
    error: Optional[str] = None
    sources_count: int = 0
    summary_preview: str = ""
    phase: str = "planning"
    research_type: str = "general"
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    visuals: List[Dict[str, Any]] = Field(default_factory=list)
    report_markdown: str = ""
    plan_notes: str = ""

    class Settings:
        name = "research_jobs"
        indexes = [[("workspace_id", 1), ("created_at", -1)]]
