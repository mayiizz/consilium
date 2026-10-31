from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import (
    CommentRequest,
    CreateTaskRequest,
    ExtractTasksResponse,
    MessageResponse,
    MoveTaskRequest,
    TaskResponse,
    UpdateTaskRequest,
)
from app.services.permissions import get_member_role, require_workspace_member
from app.services.task_service import task_service

router = APIRouter(tags=["tasks"])


@router.get("/api/workspaces/{workspace_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    workspace_id: str, user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    member = await require_workspace_member(workspace_id, user.id)
    return await task_service.list_for_workspace(workspace_id, user.id, member.role.value)


@router.post("/api/workspaces/{workspace_id}/tasks", response_model=TaskResponse)
async def create_task(
    workspace_id: str,
    data: CreateTaskRequest,
    user: User = Depends(get_current_user),
) -> TaskResponse:
    return await task_service.create(workspace_id, user.id, data)


@router.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, user: User = Depends(get_current_user)) -> TaskResponse:
    return await task_service.get(task_id, user.id)


@router.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str, data: UpdateTaskRequest, user: User = Depends(get_current_user)
) -> TaskResponse:
    return await task_service.update(task_id, user.id, data)


@router.delete("/api/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str, user: User = Depends(get_current_user)
) -> MessageResponse:
    await task_service.delete(task_id, user.id)
    return MessageResponse(message="Task deleted")


@router.post("/api/tasks/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: str, data: MoveTaskRequest, user: User = Depends(get_current_user)
) -> TaskResponse:
    return await task_service.move(task_id, user.id, data)


@router.post("/api/tasks/{task_id}/comments", response_model=TaskResponse)
async def add_comment(
    task_id: str, data: CommentRequest, user: User = Depends(get_current_user)
) -> TaskResponse:
    return await task_service.add_comment(task_id, user.id, data)


@router.post("/api/workspaces/{workspace_id}/tasks/extract", response_model=ExtractTasksResponse)
async def extract_tasks(
    workspace_id: str, user: User = Depends(get_current_user)
) -> ExtractTasksResponse:
    return await task_service.extract(workspace_id, user.id)


@router.post("/api/workspaces/{workspace_id}/tasks/rebuild", response_model=ExtractTasksResponse)
async def rebuild_tasks(
    workspace_id: str, user: User = Depends(get_current_user)
) -> ExtractTasksResponse:
    return await task_service.rebuild(workspace_id, user.id)
