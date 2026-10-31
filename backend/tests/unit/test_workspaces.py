import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspace_crud(client: AsyncClient, auth_headers: dict) -> None:
    create = await client.post(
        "/api/workspaces",
        json={"name": "Test Workspace"},
        headers=auth_headers,
    )
    assert create.status_code == 200
    ws = create.json()
    assert ws["name"] == "Test Workspace"
    assert ws["role"] == "lead"
    ws_id = ws["id"]

    listing = await client.get("/api/workspaces", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    detail = await client.get(f"/api/workspaces/{ws_id}", headers=auth_headers)
    assert detail.status_code == 200

    update = await client.put(
        f"/api/workspaces/{ws_id}",
        json={"name": "Updated Workspace"},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Updated Workspace"

    regen = await client.post(
        f"/api/workspaces/{ws_id}/regenerate-code",
        headers=auth_headers,
    )
    assert regen.status_code == 200
    assert regen.json()["invite_code"]
