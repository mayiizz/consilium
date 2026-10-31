import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_and_analytics(client: AsyncClient, auth_headers: dict) -> None:
    ws = await client.post(
        "/api/workspaces",
        json={"name": "Analytics WS"},
        headers=auth_headers,
    )
    ws_id = ws.json()["id"]

    dashboard = await client.get(f"/api/workspaces/{ws_id}/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "stats" in body
    assert "total_tasks" in body["stats"]

    roadmap = await client.get(f"/api/workspaces/{ws_id}/roadmap", headers=auth_headers)
    assert roadmap.status_code == 200
    assert "phases" in roadmap.json()

    risks = await client.get(f"/api/workspaces/{ws_id}/risks", headers=auth_headers)
    assert risks.status_code == 200
