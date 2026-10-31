from typing import List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import GitHubConnectRequest, GitHubRepoResponse, GitHubRepoSelectionRequest, GitHubStatusResponse
from app.services.github_service import github_service

router = APIRouter(tags=["github"])


@router.get("/api/github/connect")
async def github_oauth_connect(workspace_id: str = Query(...)) -> RedirectResponse:
    return await github_service.oauth_connect_url(workspace_id)


@router.get("/api/github/callback")
async def github_oauth_callback(code: str, state: str) -> RedirectResponse:
    return await github_service.oauth_callback(code, state)


@router.post("/api/workspaces/{workspace_id}/github/connect", response_model=GitHubStatusResponse)
async def connect_github(
    workspace_id: str,
    data: GitHubConnectRequest,
    user: User = Depends(get_current_user),
) -> GitHubStatusResponse:
    return await github_service.connect(workspace_id, user.id, data)


@router.delete("/api/workspaces/{workspace_id}/github/disconnect", response_model=GitHubStatusResponse)
async def disconnect_github(
    workspace_id: str, user: User = Depends(get_current_user)
) -> GitHubStatusResponse:
    return await github_service.disconnect(workspace_id, user.id)


@router.get("/api/workspaces/{workspace_id}/github/status", response_model=GitHubStatusResponse)
async def github_status(
    workspace_id: str, user: User = Depends(get_current_user)
) -> GitHubStatusResponse:
    return await github_service.status(workspace_id, user.id)


@router.get("/api/workspaces/{workspace_id}/github/repos", response_model=List[GitHubRepoResponse])
async def list_github_repos(
    workspace_id: str, user: User = Depends(get_current_user)
) -> List[GitHubRepoResponse]:
    return await github_service.list_repos(workspace_id, user.id)


@router.post("/api/workspaces/{workspace_id}/github/repo", response_model=GitHubStatusResponse)
async def select_github_repo(
    workspace_id: str,
    data: GitHubRepoSelectionRequest,
    user: User = Depends(get_current_user),
) -> GitHubStatusResponse:
    return await github_service.select_repo(workspace_id, user.id, data)


@router.post("/github/webhook")
async def github_webhook(request: Request) -> dict:
    return await github_service.handle_webhook(request)
