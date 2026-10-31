from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import (
    CreateWorkspaceRequest,
    InviteRequest,
    JoinWorkspaceRequest,
    MessageResponse,
    UpdateWorkspaceRequest,
    WorkspaceResponse,
)
from app.services.workspace_service import workspace_service

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    data: CreateWorkspaceRequest, user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    return await workspace_service.create(user.id, data)


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(user: User = Depends(get_current_user)) -> List[WorkspaceResponse]:
    return await workspace_service.list_for_user(user.id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str, user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    return await workspace_service.get(workspace_id, user.id)


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    data: UpdateWorkspaceRequest,
    user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    return await workspace_service.update(workspace_id, user.id, data)


@router.delete("/{workspace_id}", response_model=MessageResponse)
async def delete_workspace(
    workspace_id: str, user: User = Depends(get_current_user)
) -> MessageResponse:
    await workspace_service.delete(workspace_id, user.id)
    return MessageResponse(message="Workspace deleted")


@router.post("/join", response_model=WorkspaceResponse)
async def join_workspace(
    data: JoinWorkspaceRequest, user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    return await workspace_service.join(user.id, data)


@router.post("/{workspace_id}/invite", response_model=MessageResponse)
async def invite_members(
    workspace_id: str,
    data: InviteRequest,
    user: User = Depends(get_current_user),
) -> MessageResponse:
    result = await workspace_service.invite(workspace_id, user.id, data.emails)
    return MessageResponse(message=result["message"])


@router.post("/{workspace_id}/regenerate-code", response_model=WorkspaceResponse)
async def regenerate_code(
    workspace_id: str, user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    return await workspace_service.regenerate_code(workspace_id, user.id)
