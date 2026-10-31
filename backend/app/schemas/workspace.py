from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: str  # lead | member — frontend maps lead -> manager
    skills: List[str] = Field(default_factory=list)
    joined_at: datetime


class WorkspaceSettingsResponse(BaseModel):
    git_enabled: bool = True
    require_pr_merge: bool = True
    require_ci_pass: bool = False
    push_mode_enabled: bool = False


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)
    invite_emails: List[str] = Field(default_factory=list)


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    github_repo: Optional[str] = None
    settings: Optional[WorkspaceSettingsResponse] = None


class JoinWorkspaceRequest(BaseModel):
    invite_code: str


class InviteRequest(BaseModel):
    emails: List[str] = Field(min_length=1)


class WorkspaceResponse(ORMBase):
    id: str
    name: str
    slug: str
    invite_code: Optional[str] = None
    role: Optional[str] = None
    member_count: int = 0
    meeting_count: int = 0
    members: List[WorkspaceMemberResponse] = Field(default_factory=list)
    github_repo: Optional[str] = None
    github_connected: bool = False
    settings: WorkspaceSettingsResponse = Field(default_factory=WorkspaceSettingsResponse)
    created_at: datetime
    updated_at: datetime
