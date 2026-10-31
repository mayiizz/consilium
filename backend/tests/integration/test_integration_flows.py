import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/auth/register",
        json={"email": "flow@test.com", "password": "password123", "name": "Flow User"},
    )
    assert reg.status_code == 200
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    ws = await client.post("/api/workspaces", json={"name": "Flow WS"}, headers=headers)
    ws_id = ws.json()["id"]
    invite_code = ws.json()["invite_code"]

    reg2 = await client.post(
        "/api/auth/register",
        json={"email": "member@test.com", "password": "password123", "name": "Member"},
    )
    member_headers = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    join = await client.post(
        "/api/workspaces/join",
        json={"invite_code": invite_code},
        headers=member_headers,
    )
    assert join.status_code == 200
    assert join.json()["role"] == "member"

    meeting = await client.post(
        f"/api/workspaces/{ws_id}/meetings",
        json={"title": "Integration Meeting"},
        headers=headers,
    )
    meeting_id = meeting.json()["id"]

    copilot = await client.post(
        f"/api/workspaces/{ws_id}/copilot/chat",
        json={"message": "What tasks do we have?"},
        headers=headers,
    )
    assert copilot.status_code == 200
    assert copilot.json()["content"]

    task = await client.post(
        f"/api/workspaces/{ws_id}/tasks",
        json={"title": "Integration task"},
        headers=headers,
    )
    assert task.json()["task_key"].startswith("MM-")

    await client.post(f"/api/meetings/{meeting_id}/start", headers=headers)
    await client.post(f"/api/meetings/{meeting_id}/stop", headers=headers)

    gh = await client.post(
        f"/api/workspaces/{ws_id}/github/connect",
        json={"installation_id": "12345", "repo": "org/repo"},
        headers=headers,
    )
    assert gh.status_code == 200
    assert gh.json()["connected"]
