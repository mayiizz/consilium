from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class GitEvidenceLogEntryResponse(BaseModel):
    source: str = "github"
    event: str = ""
    sha: str = ""
    url: str = ""
    actor: str = ""
    message: str = ""
    at: Optional[datetime] = None


class GitEvidenceResponse(BaseModel):
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
    log: List[GitEvidenceLogEntryResponse] = Field(default_factory=list)


class TaskCommentResponse(BaseModel):
    text: str
    author_id: str
    author_name: Optional[str] = None
    created_at: datetime


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str = "To Do"
    priority: str = "medium"
    due_date: Optional[datetime] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    blocker_reason: Optional[str] = None


class MoveTaskRequest(BaseModel):
    status: str
    evidence: Optional[str] = None


class CommentRequest(BaseModel):
    text: str = Field(min_length=1)


class TaskResponse(ORMBase):
    id: str
    workspace_id: str
    meeting_id: Optional[str] = None
    source_meeting_id: Optional[str] = None
    title: str
    description: str = ""
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str
    priority: str = "medium"
    due_date: Optional[datetime] = None
    due_date_source: Optional[str] = None
    task_key: str
    is_auto_generated: bool = False
    confidence: float = 1.0
    description_user_set: bool = False
    last_activity_at: Optional[datetime] = None
    git_evidence: GitEvidenceResponse = Field(default_factory=GitEvidenceResponse)
    blocker_reason: Optional[str] = None
    comments: List[TaskCommentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ExtractTasksResponse(BaseModel):
    message: str
    job_id: str = ""
    result: Optional[dict] = None
