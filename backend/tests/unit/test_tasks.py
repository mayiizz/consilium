import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.core.security import generate_task_key
from app.utils.helpers import extract_task_keys, TASK_KEY_PATTERN


def test_task_key_format() -> None:
    key = generate_task_key()
    assert TASK_KEY_PATTERN.match(key)


def test_extract_task_keys() -> None:
    text = "Fixed bug MM-A1B2C3D4 in PR"
    keys = extract_task_keys(text)
    assert "MM-A1B2C3D4" in keys


@pytest.mark.asyncio
async def test_task_crud(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post(
        "/api/workspaces",
        json={"name": "Task WS"},
        headers=auth_headers,
    )
    ws_id = ws.json()["id"]

    create = await client.post(
        f"/api/workspaces/{ws_id}/tasks",
        json={"title": "Build API", "description": "Scaffold backend"},
        headers=auth_headers,
    )
    assert create.status_code == 200
    task = create.json()
    assert task["task_key"].startswith("MM-")
    task_id = task["id"]

    move = await client.post(
        f"/api/tasks/{task_id}/move",
        json={"status": "In Progress"},
        headers=auth_headers,
    )
    assert move.status_code == 200
    assert move.json()["status"] == "In Progress"

    comment = await client.post(
        f"/api/tasks/{task_id}/comments",
        json={"text": "Started work"},
        headers=auth_headers,
    )
    assert comment.status_code == 200
    assert len(comment.json()["comments"]) == 1


@pytest.mark.asyncio
async def test_extract_tasks_rebuilds_kanban_inline(
    client: AsyncClient, auth_headers: dict
) -> None:
    ws = await client.post(
        "/api/workspaces",
        json={"name": "Extract WS"},
        headers=auth_headers,
    )
    ws_id = ws.json()["id"]

    kanban_result = {
        "meetings": 2,
        "created": 3,
        "updated": 1,
        "review_required": 2,
        "deleted": 1,
    }
    with patch(
        "app.services.kanban_automation.rebuild_kanban_for_workspace",
        new_callable=AsyncMock,
        return_value=kanban_result,
    ) as rebuild_mock:
        response = await client.post(
            f"/api/workspaces/{ws_id}/tasks/extract",
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == kanban_result
    assert body["result"]["review_required"] == 2
    assert "3 created" in body["message"]
    rebuild_mock.assert_awaited_once_with(ws_id, fresh=True)
