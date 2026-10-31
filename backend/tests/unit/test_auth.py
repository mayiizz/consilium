import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_login_me(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/auth/register",
        json={"email": "user@test.com", "password": "securepass1", "name": "Test"},
    )
    assert reg.status_code == 200
    tokens = reg.json()
    assert "access_token" in tokens

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@test.com"

    login = await client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "securepass1"},
    )
    assert login.status_code == 200

    refresh = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
