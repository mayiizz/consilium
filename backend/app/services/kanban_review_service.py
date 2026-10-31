from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.models.kanban_review import KanbanTaskReviewQueue
from app.schemas.kanban import (
    KanbanReviewActionResponse,
    KanbanReviewItemResponse,
    KanbanReviewListResponse,
)
from app.services.kanban_agentic_automation import _normalize_status, _parse_due_date_iso, _resolve_assignee_user_id
from app.services.kanban_beanie_store import KanbanBeanieStore, workspace_member_users
from app.services.permissions import require_workspace_lead


def _item_response(item: KanbanTaskReviewQueue) -> KanbanReviewItemResponse:
    return KanbanReviewItemResponse(
        id=str(item.id),
        meeting_id=str(item.meeting_id) if item.meeting_id else None,
        candidate=item.candidate or {},
        reason=item.reason,
        created_at=item.created_at,
    )


class KanbanReviewService:
    async def list_queue(self, workspace_id: str, user_id: PydanticObjectId) -> KanbanReviewListResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws_oid = PydanticObjectId(workspace_id)
        items = await KanbanTaskReviewQueue.find(
            KanbanTaskReviewQueue.workspace_id == ws_oid,
            KanbanTaskReviewQueue.reviewed == False,
            KanbanTaskReviewQueue.deleted_at == None,
        ).sort(-KanbanTaskReviewQueue.created_at).to_list()
        return KanbanReviewListResponse(
            items=[_item_response(i) for i in items],
            total=len(items),
        )

    async def _get_pending(self, workspace_id: str, review_id: str) -> KanbanTaskReviewQueue:
        try:
            oid = PydanticObjectId(review_id)
        except Exception:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review item not found")
        item = await KanbanTaskReviewQueue.get(oid)
        if (
            not item
            or item.deleted_at
            or str(item.workspace_id) != workspace_id
            or item.reviewed
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review item not found")
        return item

    async def approve(
        self, workspace_id: str, user_id: PydanticObjectId, review_id: str
    ) -> KanbanReviewActionResponse:
        await require_workspace_lead(workspace_id, user_id)
        item = await self._get_pending(workspace_id, review_id)
        candidate = item.candidate or {}
        title = (candidate.get("title") or "").strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Candidate has no title")

        members = await workspace_member_users(workspace_id)
        assignee_name = (candidate.get("assignee") or "").strip()
        assignee_id, display_assignee = _resolve_assignee_user_id(assignee_name, members)
        src_mid = (candidate.get("source_meeting_id") or candidate.get("evidence_meeting_id") or "").strip()
        if not src_mid and item.meeting_id:
            src_mid = str(item.meeting_id)
        sync_ids = sorted({x for x in [src_mid, str(item.meeting_id) if item.meeting_id else ""] if x})

        due_dt = _parse_due_date_iso(candidate.get("due_date"))
        status_slug = _normalize_status(candidate.get("status"))
        store = KanbanBeanieStore(workspace_id)
        new_doc = {
            "title": title,
            "status": status_slug if status_slug in {"todo", "in_progress", "in_review", "done", "blockers"} else "todo",
            "assignee_id": assignee_id,
            "assignee_name": display_assignee or assignee_name,
            "due_date": due_dt,
            "source_meeting_id": src_mid or None,
            "synced_from_meeting_ids": sync_ids,
            "confidence": float(candidate.get("confidence") or 0.8),
        }
        task_id = await store.insert_task(new_doc)

        item.reviewed = True
        item.updated_at = datetime.now(timezone.utc)
        await item.save()

        return KanbanReviewActionResponse(message="Task approved and added to board", task_id=task_id)

    async def reject(
        self, workspace_id: str, user_id: PydanticObjectId, review_id: str
    ) -> KanbanReviewActionResponse:
        await require_workspace_lead(workspace_id, user_id)
        item = await self._get_pending(workspace_id, review_id)
        item.reviewed = True
        item.updated_at = datetime.now(timezone.utc)
        await item.save()
        return KanbanReviewActionResponse(message="Review item rejected")


kanban_review_service = KanbanReviewService()
