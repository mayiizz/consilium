from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.core.security import generate_invite_code, hash_password
from app.models.meeting import Meeting
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas import (
    CreateWorkspaceRequest,
    JoinWorkspaceRequest,
    UpdateWorkspaceRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceSettingsResponse,
)
from app.services.permissions import get_workspace_or_404, require_workspace_lead
from app.utils.helpers import slugify


def _settings_response(ws: Workspace) -> WorkspaceSettingsResponse:
    return WorkspaceSettingsResponse(
        git_enabled=getattr(ws.settings, "git_enabled", True),
        require_pr_merge=ws.settings.require_pr_merge,
        require_ci_pass=ws.settings.require_ci_pass,
        push_mode_enabled=ws.settings.push_mode_enabled,
    )


async def _member_responses(ws: Workspace) -> List[WorkspaceMemberResponse]:
    result = []
    for m in ws.members:
        user = await User.get(m.user_id)
        result.append(
            WorkspaceMemberResponse(
                user_id=str(m.user_id),
                name=user.name if user else None,
                email=user.email if user else None,
                role=m.role.value,
                skills=list(user.skills or []) if user else [],
                joined_at=m.joined_at,
            )
        )
    return result


async def _workspace_response(ws: Workspace, user_id: Optional[PydanticObjectId] = None) -> WorkspaceResponse:
    role = None
    if user_id:
        for m in ws.members:
            if m.user_id == user_id:
                role = m.role.value
                break
    meeting_count = await Meeting.find(
        Meeting.workspace_id == ws.id, Meeting.deleted_at == None
    ).count()
    return WorkspaceResponse(
        id=str(ws.id),
        name=ws.name,
        slug=ws.slug,
        invite_code=ws.invite_code_raw if role == WorkspaceRole.LEAD.value else None,
        role=role,
        member_count=len(ws.members),
        meeting_count=meeting_count,
        members=await _member_responses(ws),
        github_repo=ws.github_repo,
        github_connected=bool(ws.github_access_token or ws.github_app_installation_id or ws.github_repo),
        settings=_settings_response(ws),
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


class WorkspaceService:
    async def create(self, user_id: PydanticObjectId, data: CreateWorkspaceRequest) -> WorkspaceResponse:
        code = generate_invite_code()
        slug_base = slugify(data.name)
        existing = await Workspace.find({"slug": {"$regex": f"^{slug_base}"}}).to_list()
        existing_slugs = {w.slug for w in existing}
        slug = slug_base
        counter = 1
        while slug in existing_slugs:
            slug = f"{slug_base}-{counter}"
            counter += 1
        ws = Workspace(
            name=data.name,
            slug=slug,
            invite_code=hash_password(code),
            invite_code_raw=code,
            created_by=str(user_id),
            members=[
                WorkspaceMember(user_id=user_id, role=WorkspaceRole.LEAD, invited_by=user_id)
            ],
        )
        await ws.insert()
        return await _workspace_response(ws, user_id)

    async def list_for_user(self, user_id: PydanticObjectId) -> List[WorkspaceResponse]:
        workspaces = await Workspace.find(
            {"members.user_id": user_id, "deleted_at": None}
        ).to_list()
        return [await _workspace_response(ws, user_id) for ws in workspaces]

    async def get(self, workspace_id: str, user_id: PydanticObjectId) -> WorkspaceResponse:
        ws = await get_workspace_or_404(workspace_id)
        if not any(m.user_id == user_id for m in ws.members):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a member")
        return await _workspace_response(ws, user_id)

    async def update(
        self, workspace_id: str, user_id: PydanticObjectId, data: UpdateWorkspaceRequest
    ) -> WorkspaceResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        if data.name:
            ws.name = data.name
        if data.github_repo is not None:
            ws.github_repo = data.github_repo
        if data.settings:
            ws.settings.git_enabled = data.settings.git_enabled
            ws.settings.require_pr_merge = data.settings.require_pr_merge
            ws.settings.require_ci_pass = data.settings.require_ci_pass
            ws.settings.push_mode_enabled = data.settings.push_mode_enabled
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return await _workspace_response(ws, user_id)

    async def delete(self, workspace_id: str, user_id: PydanticObjectId) -> None:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        if str(ws.created_by) != str(user_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only creator can delete")
        ws.soft_delete()
        await ws.save()

    async def join(self, user_id: PydanticObjectId, data: JoinWorkspaceRequest) -> WorkspaceResponse:
        workspaces = await Workspace.find(Workspace.deleted_at == None).to_list()
        ws = None
        for candidate in workspaces:
            if verify_invite_code(data.invite_code, candidate.invite_code):
                ws = candidate
                break
        if not ws:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invalid invite code")
        if any(m.user_id == user_id for m in ws.members):
            return await _workspace_response(ws, user_id)
        ws.members.append(
            WorkspaceMember(user_id=user_id, role=WorkspaceRole.MEMBER, invited_by=None)
        )
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return await _workspace_response(ws, user_id)

    async def invite(self, workspace_id: str, user_id: PydanticObjectId, emails: List[str]) -> dict:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        return {
            "message": "Invitations queued",
            "emails": emails,
            "invite_code": ws.invite_code_raw,
        }

    async def regenerate_code(self, workspace_id: str, user_id: PydanticObjectId) -> WorkspaceResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        code = generate_invite_code()
        ws.invite_code = hash_password(code)
        ws.invite_code_raw = code
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return await _workspace_response(ws, user_id)


def verify_invite_code(raw: str, hashed: str) -> bool:
    from app.core.security import verify_password
    return verify_password(raw, hashed)


workspace_service = WorkspaceService()
