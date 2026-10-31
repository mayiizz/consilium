import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    get_settings.cache_clear()
    settings = get_settings()

    mock_client = AsyncMongoMockClient()
    db = mock_client[settings.mongodb_db_name]

    from beanie import init_beanie
    from app.models import ALL_MODELS

    await init_beanie(database=db, document_models=ALL_MODELS)
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _noop_init() -> None:
        pass

    async def _fake_connect_redis():
        return fake_redis

    patches = [
        patch("app.core.database._db", db),
        patch("app.core.database._client", mock_client),
        patch("app.core.database.get_db", lambda: db),
        patch("app.core.database.init_models", _noop_init),
        patch("app.core.database.close_db", _noop_init),
        patch("app.core.redis._redis", fake_redis),
        patch("app.core.redis.get_redis", lambda: fake_redis),
        patch("app.core.redis.connect_redis", _fake_connect_redis),
        patch("app.core.redis.close_redis", _noop_init),
    ]

    for p in patches:
        p.start()

    try:
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        for p in patches:
            p.stop()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={"email": "lead@example.com", "password": "password123", "name": "Lead User"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
