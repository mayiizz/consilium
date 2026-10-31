"""HTTP client for TinyFish Search and Agent APIs.

Official contract:
- Auth: X-API-Key
- Search: GET https://api.search.tinyfish.ai
- Agent: POST https://agent.tinyfish.ai/v1/automation/run-async
         GET  https://agent.tinyfish.ai/v1/runs/{id}
         POST https://agent.tinyfish.ai/v1/automation/run (sync, tests)
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.tinyfish.exceptions import (
    TinyFishAuthError,
    TinyFishConfigError,
    TinyFishError,
    TinyFishRateLimitError,
    TinyFishRunError,
)
from app.integrations.tinyfish.schemas import TinyFishRunResult, TinyFishSearchHit, TinyFishSearchResponse

logger = get_logger(__name__)


class TinyFishClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.tinyfish_api_key or "").strip()
        self.agent_base = (settings.tinyfish_agent_base or "https://agent.tinyfish.ai").rstrip("/")
        self.search_url = settings.tinyfish_search_url or "https://api.search.tinyfish.ai"
        self.timeout = float(settings.tinyfish_http_timeout_seconds or 60)

    def require_configured(self) -> None:
        if not self.api_key:
            raise TinyFishConfigError(
                "TINYFISH_API_KEY is not configured. Set it in backend/.env to run research."
            )

    def _headers(self) -> Dict[str, str]:
        self.require_configured()
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code in (401,):
            raise TinyFishAuthError("TinyFish rejected the API key (401)")
        if resp.status_code == 429:
            retry_after = None
            raw = resp.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    retry_after = None
            raise TinyFishRateLimitError("TinyFish rate limit exceeded", retry_after=retry_after)
        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                err = body.get("error") if isinstance(body, dict) else None
                if isinstance(err, dict):
                    detail = str(err.get("message") or err.get("code") or body)
                else:
                    detail = str(body)[:400]
            except Exception:
                detail = resp.text[:400]
            raise TinyFishError(f"TinyFish HTTP {resp.status_code}: {detail}")

    async def search(
        self,
        query: str,
        *,
        purpose: str = "",
        domain_type: str = "web",
        location: str = "US",
        language: str = "en",
    ) -> TinyFishSearchResponse:
        params: Dict[str, Any] = {"query": query, "location": location, "language": language}
        if purpose:
            params["purpose"] = purpose[:2000]
        if domain_type in ("web", "news", "research_paper"):
            params["domain_type"] = domain_type
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.search_url, headers=self._headers(), params=params)
            self._raise_for_status(resp)
            data = resp.json()
        hits = []
        for item in data.get("results") or []:
            hits.append(
                TinyFishSearchHit(
                    title=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    snippet=str(item.get("snippet") or ""),
                    site_name=str(item.get("site_name") or ""),
                    position=int(item.get("position") or 0),
                )
            )
        return TinyFishSearchResponse(
            query=str(data.get("query") or query),
            results=hits,
            total_results=int(data.get("total_results") or len(hits)),
            page=int(data.get("page") or 0),
        )

    async def run_async(self, payload: Dict[str, Any]) -> str:
        url = urljoin(self.agent_base + "/", "v1/automation/run-async")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            self._raise_for_status(resp)
            data = resp.json()
        run_id = data.get("run_id")
        if not run_id:
            raise TinyFishRunError("TinyFish run-async did not return a run_id")
        return str(run_id)

    async def get_run(self, run_id: str) -> TinyFishRunResult:
        url = urljoin(self.agent_base + "/", f"v1/runs/{run_id}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers())
            self._raise_for_status(resp)
            data = resp.json()
        return TinyFishRunResult(
            run_id=str(data.get("run_id") or run_id),
            status=str(data.get("status") or ""),
            result=data.get("result") if isinstance(data.get("result"), dict) else None,
            error=data.get("error") if isinstance(data.get("error"), dict) else None,
            goal=str(data.get("goal") or ""),
        )

    async def run_sync(self, payload: Dict[str, Any]) -> TinyFishRunResult:
        url = urljoin(self.agent_base + "/", "v1/automation/run")
        timeout = max(self.timeout, float(get_settings().tinyfish_run_timeout_seconds or 180))
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            self._raise_for_status(resp)
            data = resp.json()
        return TinyFishRunResult(
            run_id=str(data.get("run_id") or "") or None,
            status=str(data.get("status") or ""),
            result=data.get("result") if isinstance(data.get("result"), dict) else None,
            error=data.get("error") if isinstance(data.get("error"), dict) else None,
        )

    async def poll_run(
        self,
        run_id: str,
        *,
        timeout_seconds: Optional[float] = None,
        interval: float = 2.0,
    ) -> TinyFishRunResult:
        deadline = asyncio.get_event_loop().time() + float(
            timeout_seconds if timeout_seconds is not None else get_settings().tinyfish_run_timeout_seconds or 180
        )
        last: Optional[TinyFishRunResult] = None
        while asyncio.get_event_loop().time() < deadline:
            last = await self.get_run(run_id)
            status = (last.status or "").upper()
            if status in {"COMPLETED", "FAILED", "CANCELLED"}:
                return last
            await asyncio.sleep(interval)
        raise TinyFishRunError(f"TinyFish run {run_id} timed out")
