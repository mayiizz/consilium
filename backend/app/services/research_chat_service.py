"""Chat-first research: Groq conversation; TinyFish only when web evidence is needed."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.groq import GroqLLMService, GroqUnavailableError
from app.models.meeting import Meeting, MeetingStatus
from app.models.notification import ResearchJob, ResearchJobStatus
from app.models.research_conversation import (
    ResearchChatMessage,
    ResearchChatRole,
    ResearchConversation,
)
from app.models.task import Task
from app.models.workspace import Workspace
from app.schemas.notification import CreateResearchRequest
from app.schemas.research_chat import (
    ResearchChatHistoryResponse,
    ResearchChatJobSnapshot,
    ResearchChatMessageResponse,
    ResearchChatRequest,
    ResearchChatResponse,
)
from app.services.document_service import document_service
from app.services.permissions import require_workspace_lead, require_workspace_member
from app.services.research_agent_service import research_agent_service

logger = get_logger(__name__)

# Prefer answering from workspace docs / reports over starting a new web crawl.
LOCAL_CONTEXT_HINTS = (
    "last report",
    "the report",
    "this report",
    "our documents",
    "the document",
    "documents",
    "pricing table",
    "summarize",
    "rewrite",
    "from the docs",
    "in the docs",
    "project data",
    "our tasks",
    "kanban",
    "meeting notes",
)

WEB_HINTS = (
    "research",
    "look up",
    "lookup",
    "search the web",
    "search online",
    "find sources",
    "from the web",
    "latest",
    "current market",
    "competitors",
    "competitor",
    "pricing",
    "compare products",
    "official site",
    "cite",
    "sources for",
    "what's out there",
    "what is out there",
)


def _extract_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(text[start:end])
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _heuristic_needs_web(message: str) -> bool:
    lower = message.lower()
    if any(h in lower for h in LOCAL_CONTEXT_HINTS):
        return False
    if any(h in lower for h in WEB_HINTS):
        return True
    # Product / market style prompts without prior context
    if re.search(r"\b(software|saas|tools?|vendors?|startups?|market)\b", lower) and len(message) > 40:
        return True
    return False


class ResearchChatService:
    def __init__(self) -> None:
        self.llm = GroqLLMService()

    async def _get_or_create(
        self, workspace_id: str, user_id: PydanticObjectId
    ) -> ResearchConversation:
        conv = await ResearchConversation.find_one(
            ResearchConversation.workspace_id == PydanticObjectId(workspace_id),
            ResearchConversation.user_id == user_id,
            ResearchConversation.deleted_at == None,  # noqa: E711
        )
        if conv:
            return conv
        conv = ResearchConversation(
            workspace_id=PydanticObjectId(workspace_id),
            user_id=user_id,
            created_by=str(user_id),
        )
        await conv.insert()
        return conv

    async def _job_snapshot(self, job_id: Optional[str]) -> Optional[ResearchChatJobSnapshot]:
        if not job_id:
            return None
        try:
            job = await ResearchJob.get(PydanticObjectId(job_id))
        except Exception:
            return None
        if not job or job.deleted_at:
            return None
        return ResearchChatJobSnapshot(
            id=str(job.id),
            topic=job.topic or "",
            status=job.status.value if isinstance(job.status, ResearchJobStatus) else str(job.status),
            phase=job.phase or "planning",
            research_type=job.research_type or "general",
            sources_count=int(job.sources_count or 0),
            summary_preview=(job.summary_preview or "")[:600],
            document_id=str(job.document_id) if job.document_id else None,
            error=job.error,
            sources=(job.sources or [])[:12],
            tables=(job.tables or [])[:6],
        )

    def _history_text(self, messages: List[ResearchChatMessage], limit: int = 12) -> str:
        lines: List[str] = []
        for m in messages[-limit:]:
            role = m.role.value if isinstance(m.role, ResearchChatRole) else str(m.role)
            lines.append(f"{role}: {m.content}")
        return "\n".join(lines)

    async def _workspace_project_context(
        self, workspace_id: str, messages: List[ResearchChatMessage]
    ) -> str:
        """Documents + research reports + tasks + meetings for this workspace."""
        parts: List[str] = []
        wid = PydanticObjectId(workspace_id)
        settings = get_settings()
        docs_budget = max(int(settings.kanban_document_rag_max_chars or 6000), 12000)

        try:
            ws = await Workspace.get(wid)
            if ws and not ws.deleted_at:
                member_n = len(ws.members or [])
                parts.append(
                    f"## Workspace\nName: {ws.name}\nSlug: {ws.slug}\nMembers: {member_n}\n"
                    f"Git enabled: {bool(getattr(ws.settings, 'git_enabled', True))}\n"
                    f"Linked GitHub repo: {ws.github_repo or '(none)'}"
                )
        except Exception:
            logger.exception("Research chat workspace context failed")

        try:
            docs_ctx = await document_service.list_extracted_texts(
                workspace_id, max_chars=docs_budget
            )
            if docs_ctx.strip():
                parts.append(f"## Documents (Documents section)\n{docs_ctx.strip()}")
            else:
                parts.append("## Documents (Documents section)\n(No extracted document text yet.)")
        except Exception:
            logger.exception("Research chat documents context failed")

        # Prefer report attached to this chat, else latest completed job in workspace.
        report_block = ""
        for m in reversed(messages):
            if not m.research_job_id:
                continue
            try:
                job = await ResearchJob.get(PydanticObjectId(m.research_job_id))
            except Exception:
                continue
            if not job or job.deleted_at or job.status != ResearchJobStatus.DONE:
                continue
            md = (job.report_markdown or job.summary_preview or "").strip()
            if md:
                tables = ""
                if job.tables:
                    tables = f"\nTables JSON (excerpt): {json.dumps(job.tables[:4], ensure_ascii=False)[:3000]}"
                report_block = f"Most recent chat research report “{job.topic}”:\n{md[:10000]}{tables}"
                break
        if not report_block:
            try:
                jobs = (
                    await ResearchJob.find(
                        ResearchJob.workspace_id == wid,
                        ResearchJob.deleted_at == None,  # noqa: E711
                        ResearchJob.status == ResearchJobStatus.DONE,
                    )
                    .sort([("updated_at", -1)])
                    .limit(3)
                    .to_list()
                )
                chunks: List[str] = []
                for job in jobs:
                    md = (job.report_markdown or job.summary_preview or "").strip()
                    if not md:
                        continue
                    chunks.append(f"### Report: {job.topic}\n{md[:5000]}")
                if chunks:
                    report_block = "Recent workspace research reports:\n" + "\n\n".join(chunks)
            except Exception:
                logger.exception("Research chat jobs context failed")
        if report_block:
            parts.append(f"## Research reports\n{report_block}")

        try:
            tasks = (
                await Task.find(
                    Task.workspace_id == wid,
                    Task.deleted_at == None,  # noqa: E711
                )
                .sort([("updated_at", -1)])
                .limit(40)
                .to_list()
            )
            if tasks:
                lines = []
                for t in tasks:
                    st = t.status.value if hasattr(t.status, "value") else str(t.status)
                    who = t.assignee_name or "unassigned"
                    lines.append(f"- [{st}] {t.title} (assignee: {who})")
                parts.append("## Kanban / tasks\n" + "\n".join(lines))
        except Exception:
            logger.exception("Research chat tasks context failed")

        try:
            meetings = (
                await Meeting.find(
                    Meeting.workspace_id == wid,
                    Meeting.deleted_at == None,  # noqa: E711
                )
                .sort([("ended_at", -1), ("scheduled_at", -1)])
                .limit(8)
                .to_list()
            )
            mlines: List[str] = []
            for m in meetings:
                st = m.status.value if hasattr(m.status, "value") else str(m.status)
                bit = f"- {m.title} [{st}]"
                if m.summary:
                    bit += f"\n  Summary: {m.summary[:800]}"
                if m.key_decisions:
                    bit += f"\n  Decisions: {'; '.join(m.key_decisions[:8])}"
                if m.action_items:
                    bit += f"\n  Actions: {'; '.join(m.action_items[:8])}"
                # Short transcript tail for ended meetings when no summary
                if not m.summary and m.status == MeetingStatus.ENDED:
                    tr = (m.full_transcript() or "").strip()
                    if tr:
                        bit += f"\n  Transcript excerpt: {tr[-1500:]}"
                mlines.append(bit)
            if mlines:
                parts.append("## Meetings\n" + "\n".join(mlines))
        except Exception:
            logger.exception("Research chat meetings context failed")

        text = "\n\n".join(parts).strip()
        # Hard cap so prompts stay within model limits
        return text[:24000]

    async def _decide(
        self, message: str, history: str, project_context: str
    ) -> Dict[str, Any]:
        """Ask Groq whether TinyFish web research is required."""
        default = {
            "needs_web": _heuristic_needs_web(message),
            "topic": message.strip()[:500],
            "constraints": "",
            "research_type": "general",
            "reply": "",
        }
        # If the user is clearly asking about local docs/reports, never force web.
        if any(h in message.lower() for h in LOCAL_CONTEXT_HINTS):
            default["needs_web"] = False
        if not self.llm.available:
            if default["needs_web"]:
                default["reply"] = (
                    "I'll start a web research job for that once GROQ_API_KEY is configured "
                    "for planning. Starting TinyFish research based on your request."
                )
            else:
                default["reply"] = (
                    "Research chat is in offline mode. Configure GROQ_API_KEY for conversational replies, "
                    "or ask me to research a topic so TinyFish can gather sources."
                )
            return default

        system = (
            "You are Consilium Research Chat router. Decide if the user needs live web research "
            "(TinyFish search + browse of public pages) or a normal answer from workspace context.\n"
            "The assistant ALREADY has access to Documents, research reports, tasks, and meetings "
            "in the project context below — do NOT set needs_web=true just to summarize/rewrite those.\n"
            "Use web research ONLY when they need fresh external/public sources not in the workspace: "
            "new market scan, competitors online, latest pricing from the web, papers, “look this up”.\n"
            "Do NOT use web for: greetings, summarizing/rewriting last report or documents, "
            "pricing tables already in context, project/task questions, meeting follow-ups.\n"
            "Return JSON only with keys:\n"
            "needs_web (boolean), topic (string, if needs_web), constraints (string), "
            "research_type (one of: general, student_project, academic, technical, competitor_analysis), "
            "ack (string — short acknowledgement only if needs_web=true; leave empty otherwise)."
        )
        user = (
            f"Conversation so far:\n{history or '(empty)'}\n\n"
            f"Project context (excerpt):\n{(project_context or '')[:6000] or '(empty)'}\n\n"
            f"Latest user message:\n{message}"
        )
        try:
            raw = await self.llm.chat_completion(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=600,
            )
            data = _extract_json_object(raw)
            if not data:
                return default
            needs = data.get("needs_web")
            if isinstance(needs, str):
                needs = needs.strip().lower() in ("1", "true", "yes")
            elif not isinstance(needs, bool):
                needs = _heuristic_needs_web(message)
            if any(h in message.lower() for h in LOCAL_CONTEXT_HINTS):
                needs = False
            topic = str(data.get("topic") or message).strip()[:500]
            if needs and len(topic) < 3:
                topic = message.strip()[:500]
            return {
                "needs_web": bool(needs),
                "topic": topic,
                "constraints": str(data.get("constraints") or "").strip()[:2000],
                "research_type": str(data.get("research_type") or "general").strip() or "general",
                "reply": str(data.get("ack") or data.get("reply") or "").strip(),
            }
        except GroqUnavailableError:
            return default
        except Exception:
            logger.exception("Research chat decide failed")
            return default

    async def _answer_from_context(
        self, message: str, history: str, project_context: str
    ) -> str:
        if not self.llm.available:
            return (
                "Configure GROQ_API_KEY for chat replies, or ask me to research a topic "
                "so TinyFish can gather sources."
            )
        system = (
            "You are Consilium Research Chat for this workspace.\n"
            "You have access to Documents (Documents section), research reports, Kanban tasks, "
            "and meeting notes in PROJECT CONTEXT. Use that data to answer.\n"
            "When the user says “last report”, “pricing table”, or “documents”, use the research "
            "reports / Documents sections — do not claim you lack them if they appear below.\n"
            "Cite document or report titles when relevant. If something is truly missing, say so "
            "and offer to run TinyFish web research.\n"
            "You do not have live web access in this turn.\n\n"
            f"PROJECT CONTEXT:\n{project_context or '(No project data available yet.)'}"
        )
        return await self.llm.chat_completion(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Conversation:\n{history}\n\nUser: {message}",
                },
            ],
            temperature=0.35,
            max_tokens=2000,
        )

    async def chat(
        self, workspace_id: str, user_id: PydanticObjectId, data: ResearchChatRequest
    ) -> ResearchChatResponse:
        await require_workspace_lead(workspace_id, user_id)
        message = (data.message or "").strip()
        if not message:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Message is empty")

        conv = await self._get_or_create(workspace_id, user_id)
        conv.messages.append(
            ResearchChatMessage(role=ResearchChatRole.USER, content=message)
        )

        history = self._history_text(conv.messages)
        project_context = await self._workspace_project_context(workspace_id, conv.messages)
        decision = await self._decide(message, history, project_context)

        used_web = False
        job_id: Optional[str] = None
        content = ""

        if decision.get("needs_web"):
            topic = str(decision.get("topic") or message).strip()
            try:
                job = await research_agent_service.create_job(
                    workspace_id,
                    user_id,
                    CreateResearchRequest(
                        topic=topic,
                        constraints=str(decision.get("constraints") or ""),
                        research_type=str(decision.get("research_type") or "general"),
                    ),
                )
                used_web = True
                job_id = job.id
                content = (decision.get("reply") or "").strip() or (
                    f"I'll research “{topic}” on the web with TinyFish and come back with a sourced report."
                )
                content = (
                    f"{content.rstrip()}\n\n"
                    f"_Web research started — gathering sources…_"
                )
            except HTTPException as exc:
                content = f"I couldn't start web research: {exc.detail}"
            except Exception:
                logger.exception("Research chat failed to start TinyFish job")
                content = "I couldn't start web research right now. Please try again."
        else:
            try:
                content = await self._answer_from_context(message, history, project_context)
            except GroqUnavailableError as exc:
                content = str(exc)
            except Exception:
                logger.exception("Research chat answer failed")
                content = "Sorry — I couldn't answer from workspace context. Please try again."

        msg_id = str(uuid.uuid4())
        assistant = ResearchChatMessage(
            role=ResearchChatRole.ASSISTANT,
            content=content,
            message_id=msg_id,
            research_job_id=job_id,
            used_web=used_web,
        )
        conv.messages.append(assistant)
        # Cap history growth
        if len(conv.messages) > 80:
            conv.messages = conv.messages[-80:]
        await conv.save()

        job_snap = await self._job_snapshot(job_id)
        return ResearchChatResponse(
            message=ResearchChatMessageResponse(
                message_id=msg_id,
                role="assistant",
                content=content,
                timestamp=assistant.timestamp,
                used_web=used_web,
                research_job_id=job_id,
                job=job_snap,
            ),
            used_web=used_web,
            research_job_id=job_id,
        )

    async def history(
        self, workspace_id: str, user_id: PydanticObjectId
    ) -> ResearchChatHistoryResponse:
        await require_workspace_member(workspace_id, user_id)
        conv = await ResearchConversation.find_one(
            ResearchConversation.workspace_id == PydanticObjectId(workspace_id),
            ResearchConversation.user_id == user_id,
            ResearchConversation.deleted_at == None,  # noqa: E711
        )
        if not conv:
            return ResearchChatHistoryResponse(messages=[], total=0)

        out: List[ResearchChatMessageResponse] = []
        for m in conv.messages:
            mid = m.message_id or str(uuid.uuid4())
            role = m.role.value if isinstance(m.role, ResearchChatRole) else str(m.role)
            snap = await self._job_snapshot(m.research_job_id) if m.research_job_id else None
            # Enrich assistant content when a job finished after the original bubble
            content = m.content
            if (
                snap
                and snap.status == "done"
                and snap.summary_preview
                and "sourced report" not in content.lower()
                and snap.summary_preview[:80] not in content
            ):
                # Keep original; frontend shows job card. Optionally append preview once.
                pass
            out.append(
                ResearchChatMessageResponse(
                    message_id=mid,
                    role=role,
                    content=content,
                    timestamp=m.timestamp,
                    used_web=bool(m.used_web or m.research_job_id),
                    research_job_id=m.research_job_id,
                    job=snap,
                )
            )
        return ResearchChatHistoryResponse(messages=out, total=len(out))

    async def clear(self, workspace_id: str, user_id: PydanticObjectId) -> dict:
        await require_workspace_lead(workspace_id, user_id)
        conv = await ResearchConversation.find_one(
            ResearchConversation.workspace_id == PydanticObjectId(workspace_id),
            ResearchConversation.user_id == user_id,
            ResearchConversation.deleted_at == None,  # noqa: E711
        )
        if conv:
            conv.messages = []
            await conv.save()
        return {"ok": True}


research_chat_service = ResearchChatService()
