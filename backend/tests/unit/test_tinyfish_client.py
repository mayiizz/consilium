from __future__ import annotations

import socket
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.tinyfish.client import TinyFishClient
from app.integrations.tinyfish.exceptions import (
    TinyFishAuthError,
    TinyFishConfigError,
    TinyFishRateLimitError,
    TinyFishRunError,
    TinyFishSSRFError,
)
from app.integrations.tinyfish.schemas import TinyFishRunResult
from app.integrations.tinyfish.service import TinyFishService
from app.integrations.tinyfish.ssrf import validate_public_https_url


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[dict] = None,
        text: str = "",
    ):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json


class FakeAsyncClient:
    def __init__(self, handler):
        self.handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        return self.handler("GET", str(url), kwargs)

    async def post(self, url, **kwargs):
        return self.handler("POST", str(url), kwargs)


def test_missing_api_key():
    client = TinyFishClient(api_key="")
    with pytest.raises(TinyFishConfigError):
        client.require_configured()


@pytest.mark.asyncio
async def test_search_sends_auth_header():
    captured = {}

    def handler(method, url, kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["params"] = kwargs.get("params")
        return FakeResponse(
            200,
            {
                "query": "q",
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com/a",
                        "snippet": "hello",
                        "site_name": "example",
                        "position": 1,
                    }
                ],
                "total_results": 1,
                "page": 0,
            },
        )

    client = TinyFishClient(api_key="secret-key")
    with patch("app.integrations.tinyfish.client.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        result = await client.search("q", purpose="research topic", domain_type="web")
    assert captured["method"] == "GET"
    assert captured["headers"]["X-API-Key"] == "secret-key"
    assert captured["params"]["query"] == "q"
    assert captured["params"]["purpose"].startswith("research")
    assert result.results[0].url == "https://example.com/a"


@pytest.mark.asyncio
async def test_run_async_and_poll_completed():
    states = {"n": 0}

    def handler(method, url, kwargs):
        if method == "POST":
            assert "run-async" in url
            assert kwargs["json"]["url"] == "https://example.com/page"
            assert "output_schema" in kwargs["json"]
            return FakeResponse(200, {"run_id": "run-1", "status": "PENDING"})
        states["n"] += 1
        if states["n"] == 1:
            return FakeResponse(200, {"run_id": "run-1", "status": "RUNNING"})
        return FakeResponse(
            200,
            {
                "run_id": "run-1",
                "status": "COMPLETED",
                "result": {"title": "Page", "summary": "Facts", "findings": ["one"]},
            },
        )

    client = TinyFishClient(api_key="k")
    with patch("app.integrations.tinyfish.client.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        with patch("app.integrations.tinyfish.client.asyncio.sleep", AsyncMock()):
            run_id = await client.run_async(
                {"url": "https://example.com/page", "goal": "extract", "output_schema": {"type": "object"}}
            )
            assert run_id == "run-1"
            done = await client.poll_run(run_id, timeout_seconds=10, interval=0)
    assert done.status == "COMPLETED"
    assert done.result["summary"] == "Facts"


@pytest.mark.asyncio
async def test_browser_research_structured_result(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.tinyfish.ssrf.socket.getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )

    class StubClient(TinyFishClient):
        def __init__(self):
            super().__init__(api_key="k")

        async def run_async(self, payload):
            assert payload["output_schema"]["type"] == "object"
            return "abc"

        async def poll_run(self, run_id, **kwargs):
            return TinyFishRunResult(
                run_id=run_id,
                status="COMPLETED",
                result={"title": "Doc", "summary": "Extracted", "findings": ["a"]},
            )

    svc = TinyFishService(client=StubClient())
    rec = await svc.browser_research("https://example.com/doc", "Extract facts")
    assert rec.error is None
    assert "Extracted" in rec.extracted_content
    assert rec.extraction_method == "tinyfish"


@pytest.mark.asyncio
async def test_401():
    def handler(method, url, kwargs):
        return FakeResponse(401, {"error": {"message": "bad key"}})

    client = TinyFishClient(api_key="bad")
    with patch("app.integrations.tinyfish.client.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        with pytest.raises(TinyFishAuthError):
            await client.search("q")


@pytest.mark.asyncio
async def test_429():
    def handler(method, url, kwargs):
        return FakeResponse(429, {"error": {"message": "slow"}}, headers={"Retry-After": "2"})

    client = TinyFishClient(api_key="k")
    with patch("app.integrations.tinyfish.client.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        with pytest.raises(TinyFishRateLimitError) as exc:
            await client.search("q")
    assert exc.value.retry_after == 2.0


@pytest.mark.asyncio
async def test_poll_timeout():
    def handler(method, url, kwargs):
        return FakeResponse(200, {"run_id": "r", "status": "RUNNING"})

    client = TinyFishClient(api_key="k")
    with patch("app.integrations.tinyfish.client.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        with patch("app.integrations.tinyfish.client.asyncio.sleep", AsyncMock()):
            with pytest.raises(TinyFishRunError, match="timed out"):
                await client.poll_run("r", timeout_seconds=0, interval=0)


def test_ssrf_rejects():
    with pytest.raises(TinyFishSSRFError):
        validate_public_https_url("http://example.com")
    with pytest.raises(TinyFishSSRFError):
        validate_public_https_url("https://localhost/x")
    with pytest.raises(TinyFishSSRFError):
        validate_public_https_url("https://127.0.0.1/x")
    with pytest.raises(TinyFishSSRFError):
        validate_public_https_url("https://10.0.0.1/secret")
    with pytest.raises(TinyFishSSRFError):
        validate_public_https_url("https://169.254.169.254/latest")


def test_ssrf_allows_public_https(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.tinyfish.ssrf.socket.getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    assert validate_public_https_url("https://example.com/path") == "https://example.com/path"
