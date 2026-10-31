from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.tinyfish.client import TinyFishClient
from app.integrations.tinyfish.exceptions import (
    TinyFishAuthError,
    TinyFishConfigError,
    TinyFishError,
    TinyFishRateLimitError,
    TinyFishRunError,
    TinyFishSSRFError,
)
from app.integrations.tinyfish.schemas import ResearchSourceRecord, TinyFishRunResult, TinyFishSearchResponse
from app.integrations.tinyfish.ssrf import validate_public_https_url

logger = get_logger(__name__)

DEFAULT_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "source_url": {"type": "string"},
    },
}


class TinyFishService:
    def __init__(self, client: Optional[TinyFishClient] = None) -> None:
        self.client = client or TinyFishClient()

    async def search(
        self,
        query: str,
        *,
        purpose: str = "",
        domain_type: str = "web",
    ) -> TinyFishSearchResponse:
        return await self._with_retries(lambda: self.client.search(query, purpose=purpose, domain_type=domain_type))

    async def browser_research(
        self,
        url: str,
        objective: str,
        extraction_schema: dict | None = None,
    ) -> ResearchSourceRecord:
        safe_url = validate_public_https_url(url)
        goal = (
            f"{objective.strip()}\n\n"
            "Extract publicly visible information only. "
            "Do not log in, do not solve CAPTCHAs, and do not bypass paywalls or access controls. "
            "If the page is blocked, return what is visible and note the limitation."
        )
        payload: Dict[str, Any] = {
            "url": safe_url,
            "goal": goal[:8000],
            "output_schema": extraction_schema or DEFAULT_OUTPUT_SCHEMA,
            "browser_profile": "lite",
            "agent_config": {
                "max_duration_seconds": int(get_settings().tinyfish_run_timeout_seconds or 180),
            },
        }
        result = await self._run_browser(payload)
        status = (result.status or "").upper()
        extracted = _result_to_text(result.result)
        error = None
        if status == "FAILED" or result.error:
            err = result.error or {}
            error = str(err.get("message") or err.get("code") or status or "run failed")[:500]
        title = ""
        source_type = "website"
        if isinstance(result.result, dict):
            title = str(result.result.get("title") or "")[:200]
            st = result.result.get("source_type")
            if isinstance(st, str) and st.strip():
                source_type = st.strip().lower()
        verification = "unverified" if error else ("verified" if extracted else "unverified")
        return ResearchSourceRecord(
            url=safe_url,
            title=title or safe_url,
            extraction_method="tinyfish",
            extracted_content=extracted,
            extracted_data=result.result if isinstance(result.result, dict) else None,
            source_type=source_type,
            verification_status=verification,
            retrieved_at=datetime.now(timezone.utc),
            error=error,
        )

    async def _run_browser(self, payload: Dict[str, Any]) -> TinyFishRunResult:
        async def _once() -> TinyFishRunResult:
            run_id = await self.client.run_async(payload)
            return await self.client.poll_run(run_id)

        return await self._with_retries(_once)

    async def _with_retries(self, fn, attempts: int = 3):
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return await fn()
            except TinyFishRateLimitError as exc:
                last_exc = exc
                wait = exc.retry_after if exc.retry_after is not None else (2 ** i)
                logger.warning("TinyFish rate limited; retrying in %ss", wait)
                await asyncio.sleep(float(wait))
            except (TinyFishAuthError, TinyFishConfigError, TinyFishSSRFError):
                raise
            except TinyFishError as exc:
                last_exc = exc
                if i == attempts - 1:
                    raise
                await asyncio.sleep(2 ** i)
        raise last_exc or TinyFishRunError("TinyFish request failed")


def _result_to_text(result: Optional[Dict[str, Any]]) -> str:
    if not result:
        return ""
    parts: list[str] = []
    if isinstance(result.get("summary"), str) and result["summary"].strip():
        parts.append(result["summary"].strip())
    for key in ("company_name", "product_name", "positioning", "target_customers", "notes"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    plans = result.get("pricing_plans")
    if isinstance(plans, list) and plans:
        parts.append("Pricing plans:")
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            parts.append(
                "- "
                + ", ".join(
                    f"{k}={plan.get(k)}"
                    for k in (
                        "plan_name",
                        "price",
                        "currency",
                        "billing_period",
                        "per_user",
                        "free_trial",
                    )
                    if plan.get(k)
                )
            )
    for key in ("features", "integrations", "strengths", "weaknesses", "findings"):
        vals = result.get(key)
        if isinstance(vals, list) and vals:
            parts.append(f"{key}:")
            parts.extend(f"- {x}" for x in vals if x)
    tables = result.get("tables")
    if isinstance(tables, list) and tables:
        parts.append("Tables:")
        for t in tables[:5]:
            if not isinstance(t, dict):
                continue
            headers = t.get("headers") or []
            parts.append(f"caption={t.get('caption') or ''} headers={headers}")
            for row in (t.get("rows") or [])[:20]:
                parts.append(" | ".join(str(c) for c in row))
    images = result.get("image_urls")
    if isinstance(images, list) and images:
        parts.append("Images:")
        parts.extend(f"- {u}" for u in images if isinstance(u, str) and u.startswith("https://"))
    for key in ("pricing_page_url", "website", "source_url"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    if parts:
        return "\n".join(parts)[:12000]
    try:
        return json.dumps(result, ensure_ascii=False)[:12000]
    except Exception:
        return str(result)[:12000]


tinyfish_service = TinyFishService()
