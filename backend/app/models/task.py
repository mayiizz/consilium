from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import AuditMixin, utcnow


class TaskStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    BLOCKERS = "Blockers"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class GitEvidenceEntry(BaseModel):
    source: str = "github"
    event: str = ""
    sha: str = ""
    url: str = ""
    actor: str = ""
    message: str = ""
    at: Optional[datetime] = None


class GitEvidence(BaseModel):
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_title: Optional[str] = None
    commit_sha: Optional[str] = None
    merged_at: Optional[datetime] = None
    merged_by: Optional[str] = None
    ci_status: str = "unknown"
    ci_url: Optional[str] = None
    github_ci_head_sha: Optional[str] = None
    github_ci_conclusion: Optional[str] = None
    github_ci_updated_at: Optional[datetime] = None
    github_ci_workflow_url: Optional[str] = None
    github_ci_workflow_run_id: Optional[int] = None
    log: List[GitEvidenceEntry] = Field(default_factory=list)


class TaskComment(BaseModel):
    text: str
    author: PydanticObjectId
    created_at: datetime = Field(default_factory=utcnow)


class TaskHistoryEntry(BaseModel):
    field: str
    old_value: str
    new_value: str
    changed_by: PydanticObjectId
    changed_at: datetime = Field(default_factory=utcnow)


class Task(Document, AuditMixin):
    workspace_id: PydanticObjectId
    meeting_id: Optional[PydanticObjectId] = None
    source_meeting_id: Optional[PydanticObjectId] = None
    title: str
    description: str = ""
    assignee: Optional[PydanticObjectId] = None
    assignee_name: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    due_date_source: Optional[str] = None  # transcript | user | None
    task_key: Indexed(str, unique=True)
    is_auto_generated: bool = False
    confidence: float = 1.0
    evidence: Optional[str] = None
    evidence_chunk_id: Optional[int] = None
    git_evidence: GitEvidence = Field(default_factory=GitEvidence)
    blocker_reason: Optional[str] = None
    synced_from_meeting_ids: List[str] = Field(default_factory=list)
    last_activity_at: Optional[datetime] = None
    description_user_set: bool = False
    comments: List[TaskComment] = Field(default_factory=list)
    history: List[TaskHistoryEntry] = Field(default_factory=list)

    class Settings:
        name = "tasks"
