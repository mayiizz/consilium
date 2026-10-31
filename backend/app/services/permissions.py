from typing import Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


async def get_workspace_or_404(workspace_id: str) -> Workspace:
    ws = await Workspace.get(PydanticObjectId(workspace_id))
    if not ws or ws.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


def get_member_role(workspace: Workspace, user_id: PydanticObjectId) -> Optional[WorkspaceRole]:
    for m in workspace.members:
        if m.user_id == user_id:
            return m.role
    return None


async def require_workspace_member(workspace_id: str, user_id: PydanticObjectId) -> WorkspaceMember:
    ws = await get_workspace_or_404(workspace_id)
    for m in ws.members:
        if m.user_id == user_id:
            return m
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")


async def require_workspace_lead(workspace_id: str, user_id: PydanticObjectId) -> WorkspaceMember:
    member = await require_workspace_member(workspace_id, user_id)
    if member.role != WorkspaceRole.LEAD:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Lead role required")
    return member
