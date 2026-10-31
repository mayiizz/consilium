from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.integrations.tinyfish.exceptions import TinyFishRunError
from app.integrations.tinyfish.schemas import ResearchSourceRecord, TinyFishSearchHit, TinyFishSearchResponse
from app.integrations.tinyfish.service import TinyFishService
from app.models.notification import ResearchJob, ResearchJobStatus
from app.services.research_agent_service import ResearchAgentService


class FakeTinyFish(TinyFishService):
    def __init__(self, fail_url: str | None = None, empty: bool = False):
        from app.integrations.tinyfish.client import TinyFishClient

        super().__init__(client=TinyFishClient(api_key="test-key"))
        self.fail_url = fail_url
        self.empty = empty
        self.browse_calls: list[str] = []

    async def search(self, query, *, purpose="", domain_type="web"):
        if self.empty:
            return TinyFishSearchResponse(query=query, results=[])
        return TinyFishSearchResponse(
            query=query,
            results=[
                TinyFishSearchHit(title="Ok", url="https://example.com/ok", snippet="a"),
                TinyFishSearchHit(title="Fail", url="https://example.com/fail", snippet="b"),
            ],
        )

    async def browser_research(self, url, objective, extraction_schema=None):
        self.browse_calls.append(url)
        if self.fail_url and url == self.fail_url:
            raise TinyFishRunError("browser failed")
        return ResearchSourceRecord(
            url=url,
            title="Ok page",
            extraction_method="tinyfish",
            extracted_content="Useful extract about the topic.",
            retrieved_at=datetime.now(timezone.utc),
        )


@pytest.fixture
def allow_example(monkeypatch):
    monkeypatch.setattr(
        "app.services.research_agent_service.validate_public_https_url",
        lambda url: url,
    )


@pytest.mark.asyncio
async def test_partial_tinyfish_failure_does_not_fail_job(client: AsyncClient, allow_example):
    fake = FakeTinyFish(fail_url="https://example.com/fail")
    svc = ResearchAgentService(tinyfish=fake)
    svc._plan = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "research_type": "competitor_analysis",
            "domain_type": "web",
            "search_query": "Widget market",
            "search_queries": ["Widget market"],
            "extraction_goals": "Extract facts",
        }
    )
    svc._synthesize = AsyncMock(return_value="# Research: Widget market\n\nDone.")  # type: ignore[method-assign]
    job = ResearchJob(
        workspace_id=__import__("beanie").PydanticObjectId(),
        topic="Widget market",
        constraints="",
        status=ResearchJobStatus.PENDING,
        created_by=str(__import__("beanie").PydanticObjectId()),
    )
    await job.insert()
    with patch.object(svc, "_save_document", AsyncMock(return_value=str(job.workspace_id))):
        with patch("app.services.research_agent_service.notification_service.notify", AsyncMock()):
            out = await svc.run_job(str(job.id))
    assert out["ok"] is True
    refreshed = await ResearchJob.get(job.id)
    assert refreshed.status == ResearchJobStatus.DONE
    assert refreshed.phase == "completed"
    assert any(s.get("error") for s in refreshed.sources)
    assert any(not s.get("error") for s in refreshed.sources)


@pytest.mark.asyncio
async def test_empty_search_fails_job(client: AsyncClient, allow_example):
    fake = FakeTinyFish(empty=True)
    svc = ResearchAgentService(tinyfish=fake)
    svc._plan = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "research_type": "general",
            "domain_type": "web",
            "search_query": "nothing",
            "search_queries": ["nothing"],
            "extraction_goals": "extract",
        }
    )
    job = ResearchJob(
        workspace_id=__import__("beanie").PydanticObjectId(),
        topic="Empty web",
        status=ResearchJobStatus.PENDING,
        created_by=str(__import__("beanie").PydanticObjectId()),
    )
    await job.insert()
    out = await svc.run_job(str(job.id))
    assert out["ok"] is False
    assert "no usable" in out["error"].lower()


@pytest.mark.asyncio
async def test_missing_tinyfish_key_fails_job(client: AsyncClient):
    from app.integrations.tinyfish.client import TinyFishClient

    svc = ResearchAgentService(tinyfish=TinyFishService(client=TinyFishClient(api_key="")))
    job = ResearchJob(
        workspace_id=__import__("beanie").PydanticObjectId(),
        topic="Need a key",
        status=ResearchJobStatus.PENDING,
        created_by=str(__import__("beanie").PydanticObjectId()),
    )
    await job.insert()
    out = await svc.run_job(str(job.id))
    assert out["ok"] is False
    assert "TINYFISH_API_KEY" in out["error"]
    refreshed = await ResearchJob.get(job.id)
    assert refreshed.status == ResearchJobStatus.FAILED


@pytest.mark.asyncio
async def test_lead_create_member_list(client: AsyncClient, auth_headers: dict):
    with patch.object(ResearchAgentService, "_enqueue_job", lambda self, job_id: None):
        create_ws = await client.post(
            "/api/workspaces",
            json={"name": "Research WS"},
            headers=auth_headers,
        )
        assert create_ws.status_code == 200
        ws = create_ws.json()
        ws_id = ws["id"]
        invite = ws["invite_code"]

        created = await client.post(
            f"/api/workspaces/{ws_id}/research",
            json={"topic": "Open source copilots", "constraints": "2024"},
            headers=auth_headers,
        )
        assert created.status_code == 200
        assert created.json()["topic"] == "Open source copilots"
        assert created.json()["phase"] == "planning"

        member = await client.post(
            "/api/auth/register",
            json={"email": "member@test.com", "password": "password123", "name": "Member"},
        )
        member_headers = {"Authorization": f"Bearer {member.json()['access_token']}"}
        joined = await client.post(
            "/api/workspaces/join",
            json={"invite_code": invite},
            headers=member_headers,
        )
        assert joined.status_code == 200

        forbidden = await client.post(
            f"/api/workspaces/{ws_id}/research",
            json={"topic": "Should fail for member"},
            headers=member_headers,
        )
        assert forbidden.status_code == 403

        listing = await client.get(f"/api/workspaces/{ws_id}/research", headers=member_headers)
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1
