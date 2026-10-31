import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_copilot_refresh_tasks_triggers_kanban_rebuild(
    client: AsyncClient, auth_headers: dict
) -> None:
    ws = await client.post("/api/workspaces", json={"name": "Copilot WS"}, headers=auth_headers)
    ws_id = ws.json()["id"]

    kanban_result = {
        "meetings": 1,
        "created": 2,
        "updated": 1,
        "review_required": 0,
        "deleted": 0,
    }
    with patch(
        "app.services.kanban_automation.rebuild_kanban_for_workspace",
        new_callable=AsyncMock,
        return_value=kanban_result,
    ) as rebuild_mock:
        with patch(
            "app.services.copilot_service.GroqLLMService.copilot_reply",
            new_callable=AsyncMock,
            return_value="Here is your board status.",
        ):
            response = await client.post(
                f"/api/workspaces/{ws_id}/copilot/chat",
                json={"message": "Please refresh tasks from meetings"},
                headers=auth_headers,
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kanban_refresh"] == kanban_result
    assert "Refreshed Kanban" in body["content"]
    rebuild_mock.assert_awaited_once_with(ws_id, fresh=False)
