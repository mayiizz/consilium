from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.core.security import generate_task_key
from app.models.task import Task, TaskComment, TaskHistoryEntry, TaskPriority, TaskStatus
from app.models.user import User
from app.schemas import (
    CommentRequest,
    CreateTaskRequest,
    ExtractTasksResponse,
    MoveTaskRequest,
    TaskCommentResponse,
    TaskResponse,
    UpdateTaskRequest,
)
from app.services.permissions import get_workspace_or_404, require_workspace_lead, require_workspace_member
from app.services.task_stale_detection import mark_stale_tasks_in_workspace


STATUS_MAP = {s.value: s for s in TaskStatus}
PRIORITY_MAP = {p.value: p for p in TaskPriority}


def _task_response(task: Task, assignee_name: Optional[str] = None) -> TaskResponse:
    name = assignee_name
    if not name and task.assignee_name:
        name = task.assignee_name
    return TaskResponse(
        id=str(task.id),
        workspace_id=str(task.workspace_id),
        meeting_id=str(task.meeting_id) if task.meeting_id else None,
        source_meeting_id=str(task.source_meeting_id or task.meeting_id or "") or None,
        title=task.title,
        description=task.description,
        assignee_id=str(task.assignee) if task.assignee else None,
        assignee_name=name,
        status=task.status.value,
        priority=task.priority.value,
        due_date=task.due_date,
        due_date_source=getattr(task, "due_date_source", None),
        task_key=task.task_key,
        is_auto_generated=task.is_auto_generated,
        confidence=task.confidence,
        description_user_set=task.description_user_set,
        last_activity_at=task.last_activity_at or task.updated_at,
        git_evidence=task.git_evidence.model_dump(),
        blocker_reason=task.blocker_reason,
        comments=[
            TaskCommentResponse(
                text=c.text,
                author_id=str(c.author),
                created_at=c.created_at,
            )
            for c in task.comments
        ],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _unique_task_key() -> str:
    for _ in range(10):
        key = generate_task_key()
        existing = await Task.find_one(Task.task_key == key)
        if not existing:
            return key
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate task key")


class TaskService:
    async def list_for_workspace(
        self, workspace_id: str, user_id: PydanticObjectId, role: str
    ) -> List[TaskResponse]:
        await require_workspace_member(workspace_id, user_id)
        await mark_stale_tasks_in_workspace(workspace_id)
        filters = [
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.deleted_at == None,
        ]
        if role == "member":
            tasks = await Task.find(*filters, Task.assignee == user_id).to_list()
        else:
            tasks = await Task.find(*filters).to_list()
        result = []
        for t in tasks:
            name = None
            if t.assignee:
                u = await User.get(t.assignee)
                name = u.name if u else t.assignee_name
            elif t.assignee_name:
                name = t.assignee_name
            result.append(_task_response(t, name))
        return result

    async def create(
        self, workspace_id: str, user_id: PydanticObjectId, data: CreateTaskRequest
    ) -> TaskResponse:
        await require_workspace_member(workspace_id, user_id)
        status_val = STATUS_MAP.get(data.status, TaskStatus.TODO)
        priority_val = PRIORITY_MAP.get(data.priority, TaskPriority.MEDIUM)
        now = datetime.now(timezone.utc)
        task = Task(
            workspace_id=PydanticObjectId(workspace_id),
            title=data.title,
            description=data.description,
            assignee=PydanticObjectId(data.assignee_id) if data.assignee_id else None,
            status=status_val,
            priority=priority_val,
            due_date=data.due_date,
            due_date_source="user" if data.due_date else None,
            task_key=await _unique_task_key(),
            description_user_set=bool((data.description or "").strip()),
            last_activity_at=now,
            created_by=str(user_id),
        )
        await task.insert()
        if task.assignee:
            from app.services.notification_service import notification_service

            await notification_service.notify_task_assigned(
                workspace_id=workspace_id,
                task=task,
                assignee_id=task.assignee,
            )
        return _task_response(task)

    async def get(self, task_id: str, user_id: PydanticObjectId) -> TaskResponse:
        task = await self._get_task(task_id)
        await require_workspace_member(str(task.workspace_id), user_id)
        name = None
        if task.assignee:
            u = await User.get(task.assignee)
            name = u.name if u else task.assignee_name
        return _task_response(task, name)

    async def update(self, task_id: str, user_id: PydanticObjectId, data: UpdateTaskRequest) -> TaskResponse:
        task = await self._get_task(task_id)
        await require_workspace_member(str(task.workspace_id), user_id)
        now = datetime.now(timezone.utc)
        prev_assignee = task.assignee
        if data.title:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
            task.description_user_set = True
        if data.assignee_id is not None:
            task.assignee = PydanticObjectId(data.assignee_id) if data.assignee_id else None
            if data.assignee_id:
                u = await User.get(PydanticObjectId(data.assignee_id))
                task.assignee_name = u.name if u else task.assignee_name
            else:
                task.assignee_name = None
        if data.assignee_name is not None:
            task.assignee_name = data.assignee_name or None
        if data.status:
            task.status = STATUS_MAP.get(data.status, task.status)
        if data.priority:
            task.priority = PRIORITY_MAP.get(data.priority, task.priority)
        if data.due_date is not None:
            task.due_date = data.due_date
            task.due_date_source = "user"
        if data.blocker_reason is not None:
            task.blocker_reason = data.blocker_reason
        task.updated_at = now
        task.last_activity_at = now
        await task.save()
        if task.assignee and task.assignee != prev_assignee:
            from app.services.notification_service import notification_service

            await notification_service.notify_task_assigned(
                workspace_id=str(task.workspace_id),
                task=task,
                assignee_id=task.assignee,
            )
        return _task_response(task)

    async def delete(self, task_id: str, user_id: PydanticObjectId) -> None:
        task = await self._get_task(task_id)
        await require_workspace_member(str(task.workspace_id), user_id)
        task.soft_delete()
        await task.save()

    async def move(self, task_id: str, user_id: PydanticObjectId, data: MoveTaskRequest) -> TaskResponse:
        task = await self._get_task(task_id)
        await require_workspace_member(str(task.workspace_id), user_id)
        old_status = task.status.value
        new_status = STATUS_MAP.get(data.status)
        if not new_status:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        task.status = new_status
        if data.evidence:
            task.evidence = data.evidence
        task.history.append(
            TaskHistoryEntry(
                field="status",
                old_value=old_status,
                new_value=new_status.value,
                changed_by=user_id,
            )
        )
        now = datetime.now(timezone.utc)
        task.updated_at = now
        task.last_activity_at = now
        await task.save()
        return _task_response(task)

    async def add_comment(
        self, task_id: str, user_id: PydanticObjectId, data: CommentRequest
    ) -> TaskResponse:
        task = await self._get_task(task_id)
        await require_workspace_member(str(task.workspace_id), user_id)
        task.comments.append(TaskComment(text=data.text, author=user_id))
        now = datetime.now(timezone.utc)
        task.updated_at = now
        task.last_activity_at = now
        await task.save()
        u = await User.get(user_id)
        return _task_response(task, u.name if u else None)

    async def extract(self, workspace_id: str, user_id: PydanticObjectId) -> ExtractTasksResponse:
        await require_workspace_lead(workspace_id, user_id)
        from app.services.kanban_automation import rebuild_kanban_for_workspace

        result = await rebuild_kanban_for_workspace(workspace_id, fresh=True)
        created = int(result.get("created") or 0)
        updated = int(result.get("updated") or 0)
        meetings = int(result.get("meetings") or 0)
        return ExtractTasksResponse(
            message=f"Kanban rebuilt from {meetings} meeting(s): {created} created, {updated} updated",
            result=result,
        )

    async def rebuild(self, workspace_id: str, user_id: PydanticObjectId) -> ExtractTasksResponse:
        await require_workspace_lead(workspace_id, user_id)
        from app.services.kanban_automation import rebuild_kanban_for_workspace

        result = await rebuild_kanban_for_workspace(workspace_id, fresh=False)
        created = int(result.get("created") or 0)
        updated = int(result.get("updated") or 0)
        meetings = int(result.get("meetings") or 0)
        return ExtractTasksResponse(
            message=f"Kanban synced from {meetings} meeting(s): {created} created, {updated} updated",
            result=result,
        )

    async def _get_task(self, task_id: str) -> Task:
        task = await Task.get(PydanticObjectId(task_id))
        if not task or task.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task


task_service = TaskService()
