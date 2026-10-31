from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import ORMBase


class GitHubConnectRequest(BaseModel):
    installation_id: str = "local-dev"
    repo: str


class GitHubRepoSelectionRequest(BaseModel):
    owner: str
    name: str


class GitHubRepoResponse(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    private: bool = False


class GitHubStatusResponse(BaseModel):
    connected: bool
    repo: Optional[str] = None
    installation_id: Optional[str] = None
    webhook_url: Optional[str] = None
    last_event: Optional[str] = None
    github_user_login: Optional[str] = None
    webhook_enabled: bool = False
    oauth_configured: bool = False


class GitHubValidateResponse(BaseModel):
    task_id: str
    task_key: str
    meeting_claim: Optional[str] = None
    git_evidence: dict
    confidence: Optional[float] = None
    status: str
