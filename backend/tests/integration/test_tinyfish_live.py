"""Optional live TinyFish checks. Skip unless TINYFISH_API_KEY and TINYFISH_LIVE=1."""

from __future__ import annotations

import os

import pytest

from app.integrations.tinyfish.client import TinyFishClient
from app.integrations.tinyfish.service import TinyFishService

pytestmark = pytest.mark.skipif(
    os.environ.get("TINYFISH_LIVE") != "1" or not os.environ.get("TINYFISH_API_KEY"),
    reason="Set TINYFISH_LIVE=1 and TINYFISH_API_KEY to run live TinyFish tests",
)


@pytest.mark.asyncio
async def test_live_search():
    client = TinyFishClient()
    result = await client.search("python fastapi", purpose="Find official docs", domain_type="web")
    assert result.results
    assert result.results[0].url.startswith("http")


@pytest.mark.asyncio
async def test_live_browser_research():
    svc = TinyFishService()
    rec = await svc.browser_research(
        "https://example.com",
        "Extract the visible heading and a one-sentence summary of the page.",
    )
    assert rec.url.startswith("https://")
    assert rec.extracted_content or rec.error
