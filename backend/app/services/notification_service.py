from datetime import datetime, timedelta, timezone
from typing import Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.notification import Notification, NotificationType
from app.models.task import Task, TaskStatus
from app.schemas.notification import NotificationListResponse, NotificationResponse

logger = get_logger(__name__)


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        workspace_id=str(n.workspace_id),
        type=n.type.value,
        title=n.title,
        body=n.body or "",
        task_id=str(n.task_id) if n.task_id else None,
        research_job_id=str(n.research_job_id) if n.research_job_id else None,
        read_at=n.read_at,
        created_at=n.created_at,
    )


class NotificationService:
    async def notify(
        self,
        *,
        user_id: PydanticObjectId,
        workspace_id: str,
        ntype: NotificationType,
        title: str,
        body: str = "",
        task_id: Optional[PydanticObjectId] = None,
        research_job_id: Optional[PydanticObjectId] = None,
        dedupe_key: str,
    ) -> Optional[Notification]:
        existing = await Notification.find_one(
            Notification.dedupe_key == dedupe_key,
            Notification.deleted_at == None,
        )
        if existing:
            return existing
        n = Notification(
            user_id=user_id,
            workspace_id=PydanticObjectId(workspace_id),
            type=ntype,
            title=title,
            body=body,
            task_id=task_id,
            research_job_id=research_job_id,
            dedupe_key=dedupe_key,
            created_by=str(user_id),
        )
        await n.insert()
        return n

    async def notify_task_assigned(
        self,
        *,
        workspace_id: str,
        task: Task,
        assignee_id: PydanticObjectId,
    ) -> None:
        try:
            await self.notify(
                user_id=assignee_id,
                workspace_id=workspace_id,
                ntype=NotificationType.TASK_ASSIGNED,
                title="Task assigned to you",
                body=task.title,
                task_id=task.id,
                dedupe_key=f"assign:{task.id}:{assignee_id}",
            )
        except Exception:
            logger.exception("Failed to create assignment notification")

    async def list_for_user(
        self, user_id: PydanticObjectId, limit: int = 50
    ) -> NotificationListResponse:
        items = (
            await Notification.find(
                Notification.user_id == user_id,
                Notification.deleted_at == None,
            )
            .sort([("created_at", -1)])
            .limit(limit)
            .to_list()
        )
        unread = await Notification.find(
            Notification.user_id == user_id,
            Notification.deleted_at == None,
            Notification.read_at == None,
        ).count()
        return NotificationListResponse(
            items=[_to_response(n) for n in items],
            unread_count=unread,
            total=len(items),
        )

    async def mark_read(self, notification_id: str, user_id: PydanticObjectId) -> NotificationResponse:
        n = await Notification.get(PydanticObjectId(notification_id))
        if not n or n.deleted_at or n.user_id != user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")
        if not n.read_at:
            n.read_at = datetime.now(timezone.utc)
            n.updated_at = datetime.now(timezone.utc)
            await n.save()
        return _to_response(n)

    async def mark_all_read(self, user_id: PydanticObjectId) -> int:
        now = datetime.now(timezone.utc)
        unread = await Notification.find(
            Notification.user_id == user_id,
            Notification.deleted_at == None,
            Notification.read_at == None,
        ).to_list()
        for n in unread:
            n.read_at = now
            n.updated_at = now
            await n.save()
        return len(unread)

    async def send_due_soon_reminders(self) -> dict:
        settings = get_settings()
        days = max(1, int(getattr(settings, "due_reminder_days", 2) or 2))
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days)
        tasks = await Task.find(
            Task.deleted_at == None,
            Task.due_date != None,
            Task.status != TaskStatus.DONE,
        ).to_list()
        sent = 0
        skipped = 0
        for task in tasks:
            if not task.assignee or not task.due_date:
                skipped += 1
                continue
            due = task.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if due < now or due > horizon:
                skipped += 1
                continue
            day_key = due.date().isoformat()
            await self.notify(
                user_id=task.assignee,
                workspace_id=str(task.workspace_id),
                ntype=NotificationType.DUE_SOON,
                title="Task due soon",
                body=f"{task.title} — due {due.date().isoformat()}",
                task_id=task.id,
                dedupe_key=f"due:{task.id}:{day_key}",
            )
            sent += 1
        return {"sent": sent, "skipped": skipped, "horizon_days": days}


notification_service = NotificationService()
