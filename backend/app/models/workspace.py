from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import AuditMixin, utcnow


class WorkspaceRole(str, Enum):
    LEAD = "lead"
    MEMBER = "member"


class WorkspaceMember(BaseModel):
    user_id: PydanticObjectId
    role: WorkspaceRole
    joined_at: datetime = Field(default_factory=utcnow)
    invited_by: Optional[PydanticObjectId] = None


class WorkspaceSettings(BaseModel):
    git_enabled: bool = True
    require_pr_merge: bool = True
    require_ci_pass: bool = False
    push_mode_enabled: bool = False


class Workspace(Document, AuditMixin):
    name: str
    slug: Indexed(str, unique=True)
    invite_code: str
    invite_code_raw: str
    members: List[WorkspaceMember] = Field(default_factory=list)
    github_repo: Optional[str] = None
    github_app_installation_id: Optional[str] = None
    github_webhook_secret: Optional[str] = None
    github_access_token: Optional[str] = None
    github_user_login: Optional[str] = None
    github_webhook_enabled: bool = False
    github_webhook_last_event: Optional[str] = None
    github_webhook_last_at: Optional[datetime] = None
    settings: WorkspaceSettings = Field(default_factory=WorkspaceSettings)

    class Settings:
        name = "workspaces"
