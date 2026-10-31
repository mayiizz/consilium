import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_meeting_lifecycle(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post(
        "/api/workspaces",
        json={"name": "Meeting WS"},
        headers=auth_headers,
    )
    ws_id = ws.json()["id"]

    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={
            "title": "Sprint Planning",
            "platform": "jitsi",
            "generate_link": True,
        },
        headers=auth_headers,
    )
    assert create.status_code == 200
    body = create.json()
    meeting_id = body["id"]
    assert body["status"] == "scheduled"
    assert body["meeting_url"] is not None
    assert "meet.jit.si/consilium-" in body["meeting_url"]

    start = await client.post(f"/api/meetings/{meeting_id}/start", headers=auth_headers)
    assert start.status_code == 200
    assert start.json()["status"] == "ready"
    assert start.json()["started_at"] is None

    stop = await client.post(f"/api/meetings/{meeting_id}/stop", headers=auth_headers)
    assert stop.status_code == 200
    assert stop.json()["status"] == "ended"

    summary = await client.get(f"/api/meetings/{meeting_id}/summary", headers=auth_headers)
    assert summary.status_code == 200


@pytest.mark.asyncio
async def test_meeting_custom_link(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Link WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]

    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={
            "title": "Zoom Call",
            "platform": "zoom",
            "video_link": "https://zoom.us/j/123456",
            "generate_link": False,
        },
        headers=auth_headers,
    )
    assert create.status_code == 200
    assert create.json()["meeting_url"] == "https://zoom.us/j/123456"
    assert create.json()["platform"] == "zoom"


@pytest.mark.asyncio
async def test_attendance_join_leave(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Att WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]
    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={"title": "Standup"},
        headers=auth_headers,
    )
    meeting_id = create.json()["id"]

    join = await client.post(f"/api/meetings/{meeting_id}/attendance/join", headers=auth_headers)
    assert join.status_code == 200
    assert len(join.json()["attendees"]) >= 1

    leave = await client.post(f"/api/meetings/{meeting_id}/attendance/leave", headers=auth_headers)
    assert leave.status_code == 200
    attendees = leave.json()["attendees"]
    assert len(attendees) >= 1
    assert attendees[0]["leave_time"] is not None


@pytest.mark.asyncio
async def test_transcript_chunk_append(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Transcript WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]
    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={"title": "Transcript test"},
        headers=auth_headers,
    )
    meeting_id = create.json()["id"]
    await client.post(f"/api/meetings/{meeting_id}/start", headers=auth_headers)

    from app.services.meeting_service import meeting_service

    chunk, _ = await meeting_service.append_transcript_chunk(
        meeting_id,
        {"text": "Hello team, we need to ship the dashboard by Friday."},
    )
    assert chunk.text == "Hello team, we need to ship the dashboard by Friday."
    assert chunk.speaker is None

    transcript = await client.get(f"/api/meetings/{meeting_id}/transcript", headers=auth_headers)
    assert transcript.status_code == 200
    items = transcript.json()["items"]
    assert len(items) == 1
    assert items[0]["text"] == "Hello team, we need to ship the dashboard by Friday."


@pytest.mark.asyncio
async def test_process_meeting_artifacts_rebuilds_kanban(
    client: AsyncClient, auth_headers: dict
) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Artifacts WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]
    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={"title": "Planning"},
        headers=auth_headers,
    )
    meeting_id = create.json()["id"]
    await client.post(f"/api/meetings/{meeting_id}/start", headers=auth_headers)

    from app.services.meeting_service import meeting_service
    from app.workers.tasks.extraction import _process_meeting_artifacts

    await meeting_service.append_transcript_chunk(
        meeting_id,
        {"text": "Alice will update the API documentation by next Tuesday."},
    )
    await meeting_service.append_transcript_chunk(
        meeting_id,
        {"text": "Bob agreed to review the pull request before end of day."},
    )

    kanban_result = {"meetings": 1, "created": 2, "updated": 0, "review_required": 0, "deleted": 0}
    with patch(
        "app.services.kanban_automation.rebuild_kanban_for_workspace",
        new_callable=AsyncMock,
        return_value=kanban_result,
    ) as rebuild_mock:
        result = await _process_meeting_artifacts(meeting_id)

    rebuild_mock.assert_awaited_once_with(ws_id, trigger_meeting_id=meeting_id, fresh=False)
    assert result["tasks_created"] == 2
    assert result["tasks_moved"] == 0
    assert result["kanban"] == kanban_result

    summary = await client.get(f"/api/meetings/{meeting_id}/summary", headers=auth_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["summary"]
    assert len(body["action_items"]) >= 1


@pytest.mark.asyncio
async def test_delete_meeting_cascades_tasks(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Delete WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]
    create = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={"title": "To delete"},
        headers=auth_headers,
    )
    meeting_id = create.json()["id"]
    await client.post(f"/api/meetings/{meeting_id}/start", headers=auth_headers)

    from app.services.meeting_service import meeting_service

    await meeting_service.append_transcript_chunk(
        meeting_id,
        {"text": "Alice will finish the dashboard task by Friday."},
    )

    kanban_result = {"meetings": 1, "created": 0, "updated": 0}
    with patch(
        "app.services.kanban_automation.rebuild_kanban_for_workspace",
        new_callable=AsyncMock,
        return_value=kanban_result,
    ):
        await client.post(f"/api/meetings/{meeting_id}/stop", headers=auth_headers)

    from beanie import PydanticObjectId
    from app.core.security import generate_task_key
    from app.models.task import Task, TaskStatus

    task = Task(
        workspace_id=PydanticObjectId(ws_id),
        meeting_id=PydanticObjectId(meeting_id),
        title="Dashboard task",
        task_key=generate_task_key(),
        status=TaskStatus.TODO,
        is_auto_generated=True,
    )
    await task.insert()

    tasks_before = await client.get(f"/api/workspaces/{ws_id}/tasks", headers=auth_headers)
    assert any(t.get("meeting_id") == meeting_id for t in tasks_before.json())

    with patch(
        "app.services.kanban_automation.rebuild_kanban_for_workspace",
        new_callable=AsyncMock,
        return_value={"meetings": 0, "created": 0, "updated": 0},
    ) as rebuild_on_delete:
        delete = await client.delete(f"/api/meetings/{meeting_id}", headers=auth_headers)

    assert delete.status_code == 200
    assert "removed" in delete.json()["message"].lower()
    rebuild_on_delete.assert_awaited_once_with(ws_id, fresh=False)

    tasks_after = await client.get(f"/api/workspaces/{ws_id}/tasks", headers=auth_headers)
    assert not any(t.get("meeting_id") == meeting_id for t in tasks_after.json())

    meetings = await client.get(f"/api/workspaces/{ws_id}/meetings", headers=auth_headers)
    assert not any(m["id"] == meeting_id for m in meetings.json())

    gone = await client.get(f"/api/meetings/{meeting_id}", headers=auth_headers)
    assert gone.status_code == 404
