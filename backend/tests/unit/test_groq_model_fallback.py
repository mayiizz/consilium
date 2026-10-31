from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from app.integrations.groq import GroqLLMService, GroqUnavailableError


class FakeResponse:
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text or str(json_data or "")

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=req,
                response=httpx.Response(self.status_code, request=req, text=self.text),
            )


class FakeAsyncClient:
    def __init__(self, handler):
        self.handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        return self.handler(url, kwargs)


@pytest.mark.asyncio
async def test_groq_retries_on_model_404(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    calls: list[str] = []

    def handler(url, kwargs):
        model = kwargs["json"]["model"]
        calls.append(model)
        if model == "qwen/qwen3-32b":
            return FakeResponse(404, {"error": {"message": "model does not exist"}}, text="model does not exist")
        return FakeResponse(
            200,
            {"choices": [{"message": {"content": "ok from fallback"}}]},
        )

    svc = GroqLLMService()
    svc.settings.groq_api_key = "test-key"
    svc.settings.groq_model = "qwen/qwen3-32b"
    svc.settings.groq_fallback_model = "openai/gpt-oss-120b"

    with patch("app.integrations.groq.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        out = await svc.chat_completion([{"role": "user", "content": "hi"}])
    assert out == "ok from fallback"
    assert calls[0] == "qwen/qwen3-32b"
    assert "openai/gpt-oss-120b" in calls


@pytest.mark.asyncio
async def test_groq_unavailable_when_all_models_404(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()

    def handler(url, kwargs):
        return FakeResponse(404, text="missing")

    svc = GroqLLMService()
    svc.settings.groq_api_key = "test-key"
    svc.settings.groq_model = "dead-model"
    svc.settings.groq_fallback_model = "also-dead"

    with patch("app.integrations.groq.httpx.AsyncClient", lambda **k: FakeAsyncClient(handler)):
        with pytest.raises(GroqUnavailableError):
            await svc.chat_completion([{"role": "user", "content": "hi"}])
