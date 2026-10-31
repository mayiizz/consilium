"""Beanie persistence adapter for kanban_agentic_automation (workspace-scoped)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from app.core.security import generate_task_key
from app.models.kanban_review import KanbanTaskReviewQueue
from app.models.meeting import Meeting
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.services.task_key import ensure_task_key_on_task

KANBAN_SLUG_TO_STATUS = {
    "todo": TaskStatus.TODO,
    "in_progress": TaskStatus.IN_PROGRESS,
    "in_review": TaskStatus.IN_REVIEW,
    "done": TaskStatus.DONE,
    "blockers": TaskStatus.BLOCKERS,
}

STATUS_TO_KANBAN_SLUG = {
    TaskStatus.TODO: "todo",
    TaskStatus.IN_PROGRESS: "in_progress",
    TaskStatus.IN_REVIEW: "in_review",
    TaskStatus.DONE: "done",
    TaskStatus.BLOCKERS: "blockers",
}


def _kanban_slug(status: TaskStatus | str) -> str:
    if isinstance(status, TaskStatus):
        return STATUS_TO_KANBAN_SLUG.get(status, "todo")
    s = str(status).strip().lower().replace(" ", "_")
    if s in KANBAN_SLUG_TO_STATUS:
        return s
    for slug, enum_val in KANBAN_SLUG_TO_STATUS.items():
        if enum_val.value.lower().replace(" ", "_") == s:
            return slug
    return "todo"


def task_to_dict(task: Task) -> dict:
    return {
        "_id": task.id,
        "workspace_id": str(task.workspace_id),
        "project_id": str(task.workspace_id),
        "title": task.title,
        "description": task.description or None,
        "status": _kanban_slug(task.status),
        "assignee_id": str(task.assignee) if task.assignee else None,
        "assignee_name": task.assignee_name,
        "due_date": task.due_date,
        "source_meeting_id": str(task.source_meeting_id or task.meeting_id or ""),
        "synced_from_meeting_ids": list(task.synced_from_meeting_ids or []),
        "is_auto_generated": task.is_auto_generated,
        "confidence": task.confidence,
        "task_key": task.task_key,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "last_activity_at": task.last_activity_at or task.updated_at,
        "description_user_set": task.description_user_set,
        "blocker_reason": task.blocker_reason,
    }


class KanbanBeanieStore:
    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self.ws_oid = PydanticObjectId(workspace_id)

    async def list_meetings(self) -> List[dict]:
        meetings = await Meeting.find(
            Meeting.workspace_id == self.ws_oid,
            Meeting.deleted_at == None,
        ).sort(+Meeting.started_at).to_list()
        out = []
        for m in meetings:
            out.append(
                {
                    "_id": m.id,
                    "started_at": m.started_at,
                    "ended_at": m.ended_at,
                    "created_at": m.created_at,
                }
            )
        return out

    async def meeting_transcript(self, meeting_id: str) -> str:
        m = await Meeting.get(PydanticObjectId(meeting_id))
        if not m or m.deleted_at:
            return ""
        return m.full_transcript()

    async def delete_auto_tasks(self) -> int:
        tasks = await Task.find(
            Task.workspace_id == self.ws_oid,
            Task.is_auto_generated == True,
            Task.deleted_at == None,
        ).to_list()
        n = 0
        for t in tasks:
            t.deleted_at = datetime.now(timezone.utc)
            await t.save()
            n += 1
        return n

    async def find_auto_tasks(self) -> List[dict]:
        tasks = await Task.find(
            Task.workspace_id == self.ws_oid,
            Task.is_auto_generated == True,
            Task.deleted_at == None,
        ).to_list()
        return [task_to_dict(t) for t in tasks]

    async def find_task(self, task_id: str, auto_only: bool = True) -> Optional[dict]:
        try:
            oid = PydanticObjectId(task_id)
        except Exception:
            return None
        task = await Task.get(oid)
        if not task or task.deleted_at or task.workspace_id != self.ws_oid:
            return None
        if auto_only and not task.is_auto_generated:
            return None
        return task_to_dict(task)

    async def update_task(self, task_id: str, set_doc: dict, add_meeting_ids: Optional[List[str]] = None) -> None:
        task = await Task.get(PydanticObjectId(task_id))
        if not task or task.deleted_at:
            return
        now = datetime.now(timezone.utc)
        prev_assignee = task.assignee
        if "status" in set_doc:
            slug = set_doc["status"]
            task.status = KANBAN_SLUG_TO_STATUS.get(slug, task.status)
        if "due_date" in set_doc:
            task.due_date = set_doc["due_date"]
        if "due_date_source" in set_doc:
            task.due_date_source = set_doc["due_date_source"]
        if "assignee_id" in set_doc:
            aid = set_doc["assignee_id"]
            task.assignee = PydanticObjectId(aid) if aid else None
        if "assignee_name" in set_doc:
            task.assignee_name = set_doc["assignee_name"]
        if "blocker_reason" in set_doc:
            task.blocker_reason = set_doc["blocker_reason"]
        task.updated_at = now
        task.last_activity_at = set_doc.get("last_activity_at", now)
        if add_meeting_ids:
            mids = set(task.synced_from_meeting_ids or [])
            mids.update(x for x in add_meeting_ids if x)
            task.synced_from_meeting_ids = sorted(mids)
        await task.save()
        if task.assignee and task.assignee != prev_assignee:
            try:
                from app.services.notification_service import notification_service

                await notification_service.notify_task_assigned(
                    workspace_id=str(self.ws_oid),
                    task=task,
                    assignee_id=task.assignee,
                )
            except Exception:
                pass

    async def insert_task(self, doc: dict) -> str:
        now = datetime.now(timezone.utc)
        status_slug = doc.get("status", "todo")
        key = doc.get("task_key") or generate_task_key()
        while await Task.find_one(Task.task_key == key):
            key = generate_task_key()
        assignee_id = doc.get("assignee_id")
        task = Task(
            workspace_id=self.ws_oid,
            meeting_id=PydanticObjectId(doc["source_meeting_id"]) if doc.get("source_meeting_id") else None,
            source_meeting_id=PydanticObjectId(doc["source_meeting_id"]) if doc.get("source_meeting_id") else None,
            title=doc["title"],
            description=doc.get("description") or "",
            assignee=PydanticObjectId(assignee_id) if assignee_id else None,
            assignee_name=doc.get("assignee_name"),
            status=KANBAN_SLUG_TO_STATUS.get(status_slug, TaskStatus.TODO),
            due_date=doc.get("due_date"),
            due_date_source=doc.get("due_date_source"),
            task_key=key,
            is_auto_generated=True,
            confidence=float(doc.get("confidence", 0.8)),
            synced_from_meeting_ids=doc.get("synced_from_meeting_ids") or [],
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        )
        await task.insert()
        await ensure_task_key_on_task(task)
        if task.assignee:
            try:
                from app.services.notification_service import notification_service

                await notification_service.notify_task_assigned(
                    workspace_id=str(self.ws_oid),
                    task=task,
                    assignee_id=task.assignee,
                )
            except Exception:
                pass
        return str(task.id)

    async def insert_review_queue(self, doc: dict) -> None:
        await KanbanTaskReviewQueue(
            workspace_id=self.ws_oid,
            meeting_id=PydanticObjectId(doc["meeting_id"]) if doc.get("meeting_id") else None,
            candidate=doc.get("candidate", {}),
            reason=doc.get("reason", "low_confidence"),
        ).insert()

    async def delete_orphan_task(self, task_id: str) -> None:
        task = await Task.get(PydanticObjectId(task_id))
        if task and not task.deleted_at:
            task.deleted_at = datetime.now(timezone.utc)
            await task.save()

    async def write_run_log(self, meeting_id: str, payload: dict) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import get_settings

        settings = get_settings()
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db_name]
        await db.kanban_automation_runs.insert_one(
            {
                "workspace_id": self.workspace_id,
                "project_id": self.workspace_id,
                "meeting_id": meeting_id,
                "created_at": datetime.now(timezone.utc),
                "payload": payload,
            }
        )
        client.close()


async def workspace_member_users(workspace_id: str) -> List[dict]:
    ws = await Workspace.get(PydanticObjectId(workspace_id))
    if not ws:
        return []
    out: List[dict] = []
    for m in ws.members:
        u = await User.get(m.user_id)
        if u and u.name:
            out.append({"id": str(u.id), "name": u.name})
    return out
