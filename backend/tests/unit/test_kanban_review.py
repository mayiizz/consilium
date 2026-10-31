import pytest
from httpx import AsyncClient
from beanie import PydanticObjectId

from app.models.kanban_review import KanbanTaskReviewQueue


@pytest.mark.asyncio
async def test_kanban_review_queue_approve_creates_task(
    client: AsyncClient, auth_headers: dict
) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Review WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]

    item = KanbanTaskReviewQueue(
        workspace_id=PydanticObjectId(ws_id),
        candidate={
            "title": "Update API docs",
            "assignee": "Alice",
            "confidence": 0.55,
            "evidence": "Alice will update the API documentation by Tuesday.",
            "status": "todo",
        },
        reason="low_confidence",
    )
    await item.insert()
    review_id = str(item.id)

    listing = await client.get(
        f"/api/workspaces/{ws_id}/kanban/review-queue",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    approve = await client.post(
        f"/api/workspaces/{ws_id}/kanban/review-queue/{review_id}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["task_id"]

    tasks = await client.get(f"/api/workspaces/{ws_id}/tasks", headers=auth_headers)
    assert any(t["title"] == "Update API docs" for t in tasks.json())

    listing_after = await client.get(
        f"/api/workspaces/{ws_id}/kanban/review-queue",
        headers=auth_headers,
    )
    assert listing_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_kanban_store_update_task_blocker_reason(
    client: AsyncClient, auth_headers: dict
) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Blocker WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]

    from app.core.security import generate_task_key
    from app.models.task import Task, TaskStatus
    from app.services.kanban_beanie_store import KanbanBeanieStore

    task = Task(
        workspace_id=PydanticObjectId(ws_id),
        title="Blocked feature",
        task_key=generate_task_key(),
        status=TaskStatus.IN_PROGRESS,
        is_auto_generated=True,
    )
    await task.insert()
    task_id = str(task.id)

    store = KanbanBeanieStore(ws_id)
    await store.update_task(
        task_id,
        {"blocker_reason": "Waiting on third-party API access", "status": "blockers"},
        add_meeting_ids=[],
    )

    updated = await Task.get(task.id)
    assert updated is not None
    assert updated.blocker_reason == "Waiting on third-party API access"
    assert updated.status == TaskStatus.BLOCKERS
