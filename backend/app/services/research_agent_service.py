"""Topic research: TinyFish Search + browser Agent → Groq sourced markdown report."""

from __future__ import annotations

import asyncio
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.integrations.groq import GroqLLMService, GroqUnavailableError
from app.integrations.tinyfish.exceptions import TinyFishConfigError, TinyFishError, TinyFishSSRFError
from app.integrations.tinyfish.schemas import ResearchSourceRecord
from app.integrations.tinyfish.service import TinyFishService, tinyfish_service
from app.integrations.tinyfish.ssrf import validate_public_https_url
from app.models.document import DocumentType, ProjectDocument
from app.models.notification import NotificationType, ResearchJob, ResearchJobStatus
from app.schemas.notification import (
    CreateResearchRequest,
    ResearchJobListResponse,
    ResearchJobResponse,
)
from app.services.notification_service import notification_service
from app.services.permissions import require_workspace_lead, require_workspace_member
from app.services.research_exports import (
    content_type_for,
    extract_tables_from_markdown,
    job_csv_bytes,
    job_json_payload,
    job_markdown,
    markdown_to_pdf_bytes,
    safe_filename,
)
from app.services.research_schemas import (
    RESEARCH_TYPES,
    build_competitor_pricing_table,
    collect_images_from_findings,
    competitor_search_queries,
    default_goals,
    follow_urls_from_extract,
    infer_source_type,
    is_pricing_url,
    schema_for_research_type,
    synthesize_sections,
    url_priority,
)

logger = get_logger(__name__)

RESEARCH_PHASES = (
    "planning",
    "discovering",
    "browsing",
    "extracting",
    "analyzing",
    "generating",
    "completed",
)


def _job_response(job: ResearchJob) -> ResearchJobResponse:
    return ResearchJobResponse(
        id=str(job.id),
        workspace_id=str(job.workspace_id),
        topic=job.topic,
        constraints=job.constraints or "",
        status=job.status.value,
        document_id=str(job.document_id) if job.document_id else None,
        error=job.error,
        sources_count=job.sources_count or 0,
        summary_preview=job.summary_preview or "",
        phase=job.phase or "planning",
        research_type=job.research_type or "general",
        sources=list(job.sources or []),
        findings=list(job.findings or []),
        tables=list(job.tables or []),
        visuals=list(job.visuals or []),
        plan_notes=job.plan_notes or "",
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", "", ""))


def _source_dict(record: ResearchSourceRecord) -> Dict[str, Any]:
    data = record.model_dump()
    retrieved = data.get("retrieved_at")
    if isinstance(retrieved, datetime):
        data["retrieved_at"] = retrieved.isoformat()
    return data


def _normalize_research_type(raw: str | None) -> str:
    value = (raw or "general").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "student": "student_project",
        "project": "student_project",
        "competitor": "competitor_analysis",
        "market": "competitor_analysis",
        "startup": "competitor_analysis",
    }
    value = aliases.get(value, value)
    return value if value in RESEARCH_TYPES else "general"


class ResearchAgentService:
    def __init__(self, tinyfish: Optional[TinyFishService] = None) -> None:
        self.llm = GroqLLMService()
        self.tinyfish = tinyfish or tinyfish_service

    async def create_job(
        self, workspace_id: str, user_id: PydanticObjectId, data: CreateResearchRequest
    ) -> ResearchJobResponse:
        await require_workspace_lead(workspace_id, user_id)
        topic = (data.topic or "").strip()
        if len(topic) < 3:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Topic is too short")
        research_type = _normalize_research_type(getattr(data, "research_type", None))
        job = ResearchJob(
            workspace_id=PydanticObjectId(workspace_id),
            topic=topic,
            constraints=(data.constraints or "").strip(),
            research_type=research_type,
            status=ResearchJobStatus.PENDING,
            phase="planning",
            created_by=str(user_id),
        )
        await job.insert()
        self._enqueue_job(str(job.id))
        return _job_response(job)

    def _enqueue_job(self, job_id: str) -> None:
        """Prefer Celery; also schedule an in-process run if no worker is listening."""
        try:
            from app.workers.tasks.research import run_research_job

            run_research_job.delay(job_id)
        except Exception:
            logger.exception("Failed to enqueue Celery research job", extra={"job_id": job_id})

        try:
            asyncio.create_task(self._safe_run(job_id))
        except Exception:
            logger.exception("Failed to schedule in-process research job", extra={"job_id": job_id})

    async def _safe_run(self, job_id: str) -> None:
        try:
            await self.run_job(job_id)
        except Exception:
            logger.exception("In-process research job failed", extra={"job_id": job_id})

    async def retry_job(
        self, workspace_id: str, job_id: str, user_id: PydanticObjectId
    ) -> ResearchJobResponse:
        await require_workspace_lead(workspace_id, user_id)
        job = await ResearchJob.get(PydanticObjectId(job_id))
        if not job or job.deleted_at or str(job.workspace_id) != workspace_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Research job not found")
        if job.status == ResearchJobStatus.RUNNING:
            return _job_response(job)
        if job.status == ResearchJobStatus.DONE and job.document_id:
            return _job_response(job)
        job.status = ResearchJobStatus.PENDING
        job.phase = "planning"
        job.error = None
        job.sources = []
        job.findings = []
        job.tables = []
        job.visuals = []
        job.report_markdown = ""
        job.plan_notes = ""
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        self._enqueue_job(str(job.id))
        return _job_response(job)

    async def list_jobs(
        self, workspace_id: str, user_id: PydanticObjectId
    ) -> ResearchJobListResponse:
        await require_workspace_member(workspace_id, user_id)
        jobs = (
            await ResearchJob.find(
                ResearchJob.workspace_id == PydanticObjectId(workspace_id),
                ResearchJob.deleted_at == None,  # noqa: E711
            )
            .sort([("created_at", -1)])
            .limit(50)
            .to_list()
        )
        return ResearchJobListResponse(
            items=[_job_response(j) for j in jobs],
            total=len(jobs),
        )

    async def get_job(
        self, workspace_id: str, job_id: str, user_id: PydanticObjectId
    ) -> ResearchJobResponse:
        await require_workspace_member(workspace_id, user_id)
        job = await ResearchJob.get(PydanticObjectId(job_id))
        if not job or job.deleted_at or str(job.workspace_id) != workspace_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Research job not found")
        return _job_response(job)

    async def export_job(
        self, workspace_id: str, job_id: str, user_id: PydanticObjectId, fmt: str
    ) -> tuple[bytes, str, str]:
        await require_workspace_member(workspace_id, user_id)
        job = await ResearchJob.get(PydanticObjectId(job_id))
        if not job or job.deleted_at or str(job.workspace_id) != workspace_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Research job not found")
        if job.status != ResearchJobStatus.DONE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Research is not completed yet")
        fmt_l = (fmt or "md").lower()
        mime, ext = content_type_for(fmt_l)
        name = safe_filename(job.topic, ext)
        if fmt_l == "json":
            body = json.dumps(job_json_payload(job), ensure_ascii=False, indent=2).encode("utf-8")
        elif fmt_l == "csv":
            body = job_csv_bytes(job)
        elif fmt_l == "pdf":
            body = markdown_to_pdf_bytes(job_markdown(job), title=f"Research: {job.topic}")
        else:
            body = job_markdown(job).encode("utf-8")
        return body, mime, name

    async def _set_phase(self, job: ResearchJob, phase: str) -> None:
        job.phase = phase
        job.updated_at = datetime.now(timezone.utc)
        await job.save()

    async def run_job(self, job_id: str) -> dict:
        job = await ResearchJob.get(PydanticObjectId(job_id))
        if not job or job.deleted_at:
            return {"ok": False, "error": "not_found"}
        if job.status == ResearchJobStatus.DONE:
            return {"ok": True, "document_id": str(job.document_id)}
        if job.status == ResearchJobStatus.RUNNING:
            return {"ok": True, "status": "already_running"}

        job.status = ResearchJobStatus.RUNNING
        job.phase = "planning"
        job.error = None
        job.updated_at = datetime.now(timezone.utc)
        await job.save()

        try:
            self.tinyfish.client.require_configured()

            hint = _normalize_research_type(job.research_type)
            plan = await self._plan(job.topic, job.constraints, hint)
            rtype = _normalize_research_type(str(plan.get("research_type") or hint))
            plan["research_type"] = rtype
            if not plan.get("search_query"):
                plan["search_query"] = job.topic
            if not plan.get("search_queries"):
                plan["search_queries"] = [plan["search_query"]]
            if not plan.get("extraction_goals") or rtype == "competitor_analysis":
                plan["extraction_goals"] = default_goals(rtype, job.topic, job.constraints or "")
            if plan.get("domain_type") not in ("web", "news", "research_paper"):
                plan["domain_type"] = "web"
            if rtype == "competitor_analysis":
                plan["search_queries"] = list(
                    dict.fromkeys(
                        [
                            *(plan.get("search_queries") or []),
                            *competitor_search_queries(job.topic, job.constraints or ""),
                        ]
                    )
                )[:4]
            job.research_type = rtype
            job.plan_notes = json.dumps(plan, ensure_ascii=False)[:4000]
            await self._set_phase(job, "discovering")

            purpose = job.topic if not job.constraints else f"{job.topic}. Constraints: {job.constraints}"
            queries = plan.get("search_queries") or [plan["search_query"]]
            if rtype == "competitor_analysis":
                # Prefer official sites + pricing discovery queries
                queries = list(dict.fromkeys([*queries, *competitor_search_queries(job.topic, job.constraints or "")]))
            all_hits = []
            for q in queries[:4]:
                search = await self.tinyfish.search(
                    q,
                    purpose=purpose
                    + (
                        " Prefer each competitor's official website and official pricing page."
                        if rtype == "competitor_analysis"
                        else ""
                    ),
                    domain_type=plan["domain_type"],
                )
                all_hits.extend(search.results)
            cap = None
            if rtype == "competitor_analysis":
                settings = get_settings()
                cap = max(int(settings.tinyfish_max_sites or 5), 8)
            urls = self._select_urls(all_hits, prefer_pricing=(rtype == "competitor_analysis"), cap=cap)
            if not urls:
                raise RuntimeError("TinyFish Search returned no usable public https URLs")

            extraction_schema = schema_for_research_type(plan["research_type"])
            await self._set_phase(job, "browsing")
            records, findings = await self._browse_url_list(
                urls,
                goals=plan["extraction_goals"],
                extraction_schema=extraction_schema,
                follow_pricing=(rtype == "competitor_analysis"),
                max_total=cap or get_settings().tinyfish_max_sites or 5,
            )

            await self._set_phase(job, "extracting")
            job.sources = [_source_dict(r) for r in records]
            job.findings = findings
            job.sources_count = len([r for r in records if r.extracted_content and not r.error])
            await job.save()

            successes = [r for r in records if r.extracted_content and not r.error]
            if not successes:
                raise RuntimeError("No TinyFish browser extracts succeeded; see sources for errors")

            await self._set_phase(job, "analyzing")
            pages = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.extracted_content[:400],
                    "text": r.extracted_content,
                    "source_type": r.source_type,
                    "extracted_data": r.extracted_data or {},
                }
                for r in successes
            ]
            await self._set_phase(job, "generating")
            markdown = await self._synthesize(
                job.topic,
                job.constraints,
                pages,
                research_type=plan["research_type"],
            )
            tables = extract_tables_from_markdown(markdown)
            # Prefer structured pricing/feature tables from competitor extracts
            page_tables: List[Dict[str, Any]] = []
            for f in findings:
                data = f.get("extracted_data") if isinstance(f.get("extracted_data"), dict) else {}
                for t in data.get("tables") or []:
                    if isinstance(t, dict) and (t.get("headers") or t.get("rows")):
                        page_tables.append(
                            {
                                "title": t.get("caption")
                                or f"{f.get('title') or 'Source'} table",
                                "headers": t.get("headers") or [],
                                "rows": t.get("rows") or [],
                            }
                        )
            pricing_table = build_competitor_pricing_table(findings) if rtype == "competitor_analysis" else None
            merged_tables: List[Dict[str, Any]] = []
            if pricing_table:
                merged_tables.append(pricing_table)
            merged_tables.extend(page_tables)
            merged_tables.extend(tables)
            visuals = collect_images_from_findings(findings)
            job.tables = merged_tables
            job.visuals = visuals
            if visuals and "## Product visuals" in markdown:
                # Append attributed images if the model omitted them
                if "![" not in markdown:
                    extra = ["", "## Product visuals (extracted)", ""]
                    for img in visuals[:12]:
                        cap = img.get("caption") or "Product image"
                        extra.append(f"![{cap}]({img['url']})")
                        if img.get("source_url"):
                            extra.append(f"*Source: [{img['source_url']}]({img['source_url']})*")
                        extra.append("")
                    markdown = markdown.rstrip() + "\n" + "\n".join(extra)
            job.report_markdown = markdown
            doc_id = await self._save_document(
                workspace_id=str(job.workspace_id),
                user_id=PydanticObjectId(job.created_by) if job.created_by else None,
                topic=job.topic,
                markdown=markdown,
            )
            preview = markdown.strip().split("\n", 1)[0][:240]
            job.status = ResearchJobStatus.DONE
            job.phase = "completed"
            job.document_id = PydanticObjectId(doc_id)
            job.summary_preview = preview
            job.updated_at = datetime.now(timezone.utc)
            await job.save()

            if job.created_by:
                try:
                    await notification_service.notify(
                        user_id=PydanticObjectId(job.created_by),
                        workspace_id=str(job.workspace_id),
                        ntype=NotificationType.RESEARCH_DONE,
                        title="Research report ready",
                        body=job.topic,
                        research_job_id=job.id,
                        dedupe_key=f"research_done:{job.id}",
                    )
                except Exception:
                    logger.exception("Failed to notify research completion")

            return {"ok": True, "document_id": doc_id, "sources": job.sources_count}
        except TinyFishConfigError as exc:
            return await self._fail_job(job, str(exc), job_id)
        except Exception as exc:
            logger.exception("Research job failed", extra={"job_id": job_id})
            return await self._fail_job(job, str(exc)[:800], job_id)

    async def _fail_job(self, job: ResearchJob, error: str, job_id: str) -> dict:
        job.status = ResearchJobStatus.FAILED
        job.error = error
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        return {"ok": False, "error": error}

    async def _plan(self, topic: str, constraints: str, hint: str = "general") -> Dict[str, Any]:
        fallback = {
            "research_type": hint if hint in RESEARCH_TYPES else "general",
            "domain_type": "research_paper" if hint in ("student_project", "academic") else "web",
            "search_query": topic if not constraints else f"{topic} {constraints}",
            "search_queries": [
                topic if not constraints else f"{topic} {constraints}",
            ],
            "extraction_goals": default_goals(hint if hint in RESEARCH_TYPES else "general", topic, constraints),
        }
        if hint == "competitor_analysis":
            fallback["search_queries"] = competitor_search_queries(topic, constraints)
        elif hint in ("student_project", "academic", "technical"):
            fallback["search_queries"] = [
                f"{topic} github",
                f"{topic} dataset OR arxiv OR paper",
                f"{topic} documentation",
            ]
            fallback["domain_type"] = "research_paper" if hint == "academic" else "web"

        if not self.llm.available:
            return fallback
        prompt = f"""Plan a web research job for Consilium.
Topic: {topic}
Constraints: {constraints or "none"}
User hint research_type: {hint}

Return JSON only with keys:
- research_type: one of {list(RESEARCH_TYPES)}
- domain_type: one of "web", "news", "research_paper"
- search_query: primary concise search string
- search_queries: array of 1-4 search strings (discovery)
- extraction_goals: what a browser agent should extract from each page
Never invent URLs. Prefer authoritative sources for the research_type.
If research_type is competitor_analysis, search_queries MUST include official competitor websites and pricing pages (e.g. "<competitor> pricing").
"""
        try:
            raw = await self.llm.chat_completion(
                [
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                rtype = _normalize_research_type(str(data.get("research_type") or hint))
                domain = str(data.get("domain_type") or fallback["domain_type"]).strip()
                if domain not in ("web", "news", "research_paper"):
                    domain = fallback["domain_type"]
                query = str(data.get("search_query") or fallback["search_query"]).strip()
                queries = data.get("search_queries")
                if not isinstance(queries, list) or not queries:
                    queries = [query]
                queries = [str(q).strip() for q in queries if str(q).strip()][:4]
                if rtype == "competitor_analysis":
                    queries = list(
                        dict.fromkeys([*queries, *competitor_search_queries(topic, constraints)])
                    )[:4]
                goals = str(data.get("extraction_goals") or default_goals(rtype, topic, constraints)).strip()
                if rtype == "competitor_analysis":
                    # Always use the pricing/image/table-focused goal
                    goals = default_goals(rtype, topic, constraints)
                return {
                    "research_type": rtype,
                    "domain_type": domain,
                    "search_query": query,
                    "search_queries": queries or [query],
                    "extraction_goals": goals,
                }
        except (GroqUnavailableError, json.JSONDecodeError, Exception):
            logger.warning("Research plan fallback used")
        return fallback

    def _select_urls(
        self,
        hits,
        *,
        prefer_pricing: bool = False,
        cap: int | None = None,
    ) -> List[Dict[str, str]]:
        settings = get_settings()
        if cap is None:
            cap = max(1, int(settings.tinyfish_max_sites or settings.research_max_pages or 5))
            cap = min(cap, max(1, int(settings.research_max_pages or 5)))
        else:
            cap = max(1, int(cap))
        candidates: List[Dict[str, str]] = []
        seen: set[str] = set()
        for hit in hits:
            url = getattr(hit, "url", None) or (hit.get("url") if isinstance(hit, dict) else "")
            title = getattr(hit, "title", None) or (hit.get("title") if isinstance(hit, dict) else "")
            if not url:
                continue
            try:
                validate_public_https_url(url)
            except TinyFishSSRFError:
                continue
            key = _normalize_url(url)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"url": url, "title": title or url})
        if prefer_pricing:
            candidates.sort(
                key=lambda h: url_priority(h["url"], h.get("title") or ""),
                reverse=True,
            )
        return candidates[:cap]

    async def _browse_url_list(
        self,
        urls: List[Dict[str, str]],
        *,
        goals: str,
        extraction_schema: dict,
        follow_pricing: bool = False,
        max_total: int = 5,
    ) -> tuple[List[ResearchSourceRecord], List[Dict[str, Any]]]:
        records: List[ResearchSourceRecord] = []
        findings: List[Dict[str, Any]] = []
        seen: set[str] = set()
        queue: List[Dict[str, str]] = list(urls)
        max_total = max(1, int(max_total))

        while queue and len(seen) < max_total:
            hit = queue.pop(0)
            key = _normalize_url(hit["url"])
            if key in seen:
                continue
            seen.add(key)
            try:
                record = await self.tinyfish.browser_research(
                    hit["url"],
                    goals,
                    extraction_schema=extraction_schema,
                )
            except TinyFishSSRFError as exc:
                record = ResearchSourceRecord(
                    url=hit["url"],
                    title=hit.get("title") or hit["url"],
                    extracted_content="",
                    retrieved_at=datetime.now(timezone.utc),
                    error=str(exc),
                    verification_status="unverified",
                )
            except TinyFishError as exc:
                logger.warning("TinyFish browse failed for %s: %s", hit["url"], exc)
                record = ResearchSourceRecord(
                    url=hit["url"],
                    title=hit.get("title") or hit["url"],
                    extracted_content="",
                    retrieved_at=datetime.now(timezone.utc),
                    error=str(exc)[:500],
                    verification_status="unverified",
                )
            if not record.title:
                record.title = hit.get("title") or record.url
            record.source_type = infer_source_type(record.url, record.extracted_data)
            records.append(record)
            if record.extracted_content and not record.error:
                findings.append(
                    {
                        "url": record.url,
                        "title": record.title,
                        "source_type": record.source_type,
                        "verification_status": record.verification_status,
                        "content": record.extracted_content[:4000],
                        "extracted_data": record.extracted_data or {},
                    }
                )
            if follow_pricing and record.extracted_data and not record.error:
                for follow in follow_urls_from_extract(record.url, record.extracted_data):
                    try:
                        validate_public_https_url(follow)
                    except TinyFishSSRFError:
                        continue
                    fkey = _normalize_url(follow)
                    if fkey in seen:
                        continue
                    # Prioritize pricing pages in the follow queue
                    item = {"url": follow, "title": follow}
                    if is_pricing_url(follow):
                        queue.insert(0, item)
                    else:
                        queue.append(item)
        return records, findings

    async def _synthesize(
        self,
        topic: str,
        constraints: str,
        pages: List[dict],
        *,
        research_type: str = "general",
    ) -> str:
        settings = get_settings()
        max_total = max(2000, int(settings.research_max_total_chars or 24000))
        max_page = max(500, int(settings.research_max_chars_per_page or 8000))
        chunks: List[str] = []
        used = 0
        for p in pages:
            text = (p.get("text") or p.get("snippet") or "")[:max_page]
            data = p.get("extracted_data") or {}
            extra = ""
            if data:
                try:
                    extra = "\nStructured: " + json.dumps(data, ensure_ascii=False)[:2000]
                except Exception:
                    extra = ""
            block = (
                f"### {p.get('title') or p['url']}\n"
                f"URL: {p['url']}\n"
                f"source_type: {p.get('source_type') or 'website'}\n"
                f"{text}{extra}"
            )
            if used + len(block) > max_total:
                break
            chunks.append(block)
            used += len(block)
        corpus = "\n\n".join(chunks) if chunks else "No page text extracted."
        sections = "\n".join(f"- {s}" for s in synthesize_sections(research_type))
        competitor_extra = ""
        if research_type == "competitor_analysis":
            competitor_extra = (
                "\nFor competitor_analysis: dedicate a subsection to EACH competitor website. "
                "Build a pricing markdown table using ONLY exact price/currency/billing from extracts. "
                "Include feature comparison. Embed product images with ![caption](https...) only from extracted image_urls. "
                "Prefer pricing_page_url links in Sources.\n"
            )
        prompt = f"""Write a sourced research brief in markdown.

Topic: {topic}
Constraints: {constraints or "none"}
Research type: {research_type}
{competitor_extra}
Use ONLY the source extracts below. Cite real URLs inline as markdown links.
Never invent prices, GitHub repos, papers, datasets, or URLs.
Clearly label recommendations as analysis (not verified facts).
When comparison data exists, include markdown tables.

Required sections:
# Research: {topic}
{sections}

Extracts:
{corpus}
"""
        try:
            return await self.llm.chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "You write careful, sourced research briefs with tables when useful. "
                            "Never invent URLs, prices, or citations."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=3500,
            )
        except GroqUnavailableError:
            return self._fallback_report(topic, constraints, pages)

    def _fallback_report(self, topic: str, constraints: str, pages: List[dict]) -> str:
        lines = [
            f"# Research: {topic}",
            "",
            "## Executive summary",
            f"Automated web scan for **{topic}**"
            + (f" (focus: {constraints})" if constraints else "")
            + ". Groq was unavailable; this is a source list with extracts.",
            "",
            "## Key findings",
        ]
        for i, p in enumerate(pages, start=1):
            snip = (p.get("snippet") or p.get("text") or "")[:280]
            lines.append(f"{i}. {p.get('title') or p['url']}: {snip}")
        lines.extend(["", "## Sources"])
        for p in pages:
            lines.append(f"- [{p.get('title') or p['url']}]({p['url']})")
        lines.extend(
            [
                "",
                "## Recommendations (analysis)",
                "- Re-run with Groq configured for a synthesized analysis.",
                "",
                "## Confidence notes",
                "- Low confidence: extracts only; claims not verified by LLM synthesis.",
            ]
        )
        return "\n".join(lines)

    async def _save_document(
        self,
        *,
        workspace_id: str,
        user_id: Optional[PydanticObjectId],
        topic: str,
        markdown: str,
    ) -> str:
        content = markdown.encode("utf-8")
        safe_topic = re.sub(r"[^\w\-]+", "_", topic.strip())[:60] or "topic"
        filename = f"research_{safe_topic}.md"
        db = get_db()
        bucket = AsyncIOMotorGridFSBucket(db)
        file_id = await bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "workspace_id": workspace_id,
                "mime_type": "text/markdown",
                "kind": "research",
            },
        )
        uploader = user_id
        if not uploader:
            from app.models.workspace import Workspace

            ws = await Workspace.get(PydanticObjectId(workspace_id))
            if ws and ws.members:
                uploader = ws.members[0].user_id
        if not uploader:
            raise RuntimeError("No uploader for research document")
        doc = ProjectDocument(
            workspace_id=PydanticObjectId(workspace_id),
            name=filename,
            type=DocumentType.RESEARCH,
            file_id=str(file_id),
            file_size=len(content),
            mime_type="text/markdown",
            extracted_text=markdown,
            uploaded_by=uploader,
            created_by=str(uploader),
        )
        await doc.insert()
        return str(doc.id)


research_agent_service = ResearchAgentService()
