import uuid
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import HTTPException

from app.core.logging import get_logger
from app.integrations.groq import GroqLLMService
from app.models.copilot_conversation import CopilotConversation, CopilotFeedback, CopilotMessage, CopilotRole
from app.schemas.copilot import (
    CopilotChatRequest,
    CopilotHistoryResponse,
    CopilotMessageResponse,
)
from app.services.permissions import require_workspace_member, require_workspace_lead

logger = get_logger(__name__)

KANBAN_REFRESH_KEYWORDS = (
    "refresh tasks",
    "sync kanban",
    "extract tasks",
    "update board",
    "update kanban",
    "sync tasks from meetings",
    "refresh kanban",
)


def _wants_kanban_refresh(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in KANBAN_REFRESH_KEYWORDS)


def _parse_research_request(message: str) -> str | None:
    """Return topic if message starts with 'research ' / 'research:'."""
    lower = message.strip()
    prefixes = ("research ", "research:", "research —", "research -")
    for p in prefixes:
        if lower.lower().startswith(p):
            topic = message.strip()[len(p) :].strip()
            return topic or None
    if lower.lower().strip() == "research":
        return None
    return None


class CopilotService:
    def __init__(self) -> None:
        self.llm = GroqLLMService()

    async def chat(
        self, workspace_id: str, user_id: PydanticObjectId, data: CopilotChatRequest
    ) -> CopilotMessageResponse:
        await require_workspace_member(workspace_id, user_id)
        conv = await CopilotConversation.find_one(
            CopilotConversation.workspace_id == PydanticObjectId(workspace_id),
            CopilotConversation.user_id == user_id,
            CopilotConversation.deleted_at == None,
        )
        if not conv:
            conv = CopilotConversation(
                workspace_id=PydanticObjectId(workspace_id),
                user_id=user_id,
                created_by=str(user_id),
            )
            await conv.insert()

        conv.messages.append(
            CopilotMessage(role=CopilotRole.USER, content=data.message)
        )

        kanban_refresh: dict | None = None
        if _wants_kanban_refresh(data.message):
            try:
                await require_workspace_lead(workspace_id, user_id)
                from app.services.kanban_automation import rebuild_kanban_for_workspace

                kanban_refresh = await rebuild_kanban_for_workspace(workspace_id, fresh=False)
            except HTTPException:
                pass
            except Exception:
                logger.exception("Copilot kanban refresh failed", extra={"workspace_id": workspace_id})

        research_job_line: str | None = None
        research_topic = _parse_research_request(data.message)
        if research_topic:
            try:
                await require_workspace_lead(workspace_id, user_id)
                from app.schemas.notification import CreateResearchRequest
                from app.services.research_agent_service import research_agent_service

                job = await research_agent_service.create_job(
                    workspace_id,
                    user_id,
                    CreateResearchRequest(topic=research_topic, constraints=""),
                )
                research_job_line = (
                    f"Started research job for “{research_topic}” (status: {job.status}). "
                    f"Open Research in the sidebar to track it; the report will also appear under Documents."
                )
            except HTTPException as exc:
                research_job_line = f"Could not start research: {exc.detail}"
            except Exception:
                logger.exception("Copilot research enqueue failed", extra={"workspace_id": workspace_id})
                research_job_line = "Could not start research right now. Try again from the Research page."

        context_parts: list[str] = []

        if data.meeting_id:
            from app.models.meeting import Meeting
            from app.core.config import get_settings

            meeting = await Meeting.get(PydanticObjectId(data.meeting_id))
            if meeting and not meeting.deleted_at and str(meeting.workspace_id) == workspace_id:
                parts = [f"Meeting: {meeting.title}"]
                transcript = meeting.full_transcript()
                rag_used = False
                if transcript and get_settings().kanban_rag_enabled:
                    try:
                        from app.services.transcript_rag import (
                            TranscriptRAGIndex,
                            retrieve_context_for_user_query,
                        )

                        mid = str(meeting.id)
                        idx = TranscriptRAGIndex.from_meeting_texts({mid: transcript}, {mid: 0})
                        if idx is not None:
                            ctx, _sc = retrieve_context_for_user_query(idx, mid, data.message)
                            if (ctx or "").strip():
                                parts.append(f"Retrieved transcript context (RAG):\n{ctx}")
                                rag_used = True
                    except Exception:
                        logger.exception("Copilot transcript RAG failed", extra={"meeting_id": data.meeting_id})
                if not rag_used and transcript:
                    parts.append(f"Transcript:\n{transcript[:6000]}")
                if meeting.summary:
                    parts.append(f"Summary: {meeting.summary}")
                if meeting.key_decisions:
                    parts.append(f"Key decisions: {'; '.join(meeting.key_decisions)}")
                if meeting.action_items:
                    parts.append(f"Action items: {'; '.join(meeting.action_items)}")
                context_parts.append("\n\n".join(parts))

        try:
            from app.core.config import get_settings
            from app.services.document_service import document_service

            if get_settings().kanban_document_rag_enabled:
                docs_ctx = await document_service.list_extracted_texts(
                    workspace_id,
                    max_chars=int(get_settings().kanban_document_rag_max_chars or 6000),
                )
                if docs_ctx.strip():
                    context_parts.append(f"Workspace documents:\n{docs_ctx}")
        except Exception:
            logger.exception("Copilot document context failed", extra={"workspace_id": workspace_id})

        context = "\n\n".join(context_parts)

        history = "\n".join(
            f"{m.role.value}: {m.content}" for m in conv.messages[-5:]
        )
        reply = await self.llm.copilot_reply(data.message, context, history)
        if research_job_line:
            reply = f"{research_job_line}\n\n{reply.rstrip()}"
        if kanban_refresh:
            created = int(kanban_refresh.get("created") or 0)
            updated = int(kanban_refresh.get("updated") or 0)
            meetings = int(kanban_refresh.get("meetings") or 0)
            refresh_line = (
                f"\n\nRefreshed Kanban: {created} created, {updated} updated from {meetings} meeting(s)."
            )
            reply = f"{reply.rstrip()}{refresh_line}"
        msg_id = str(uuid.uuid4())
        conv.messages.append(
            CopilotMessage(
                role=CopilotRole.ASSISTANT,
                content=reply,
                message_id=msg_id,
            )
        )
        conv.updated_at = datetime.now(timezone.utc)
        await conv.save()

        return CopilotMessageResponse(
            message_id=msg_id,
            role="assistant",
            content=reply,
            timestamp=datetime.now(timezone.utc),
            kanban_refresh=kanban_refresh,
        )

    async def feedback(
        self, workspace_id: str, user_id: PydanticObjectId, message_id: str, feedback: str
    ) -> None:
        await require_workspace_member(workspace_id, user_id)
        conv = await CopilotConversation.find_one(
            CopilotConversation.workspace_id == PydanticObjectId(workspace_id),
            CopilotConversation.user_id == user_id,
            CopilotConversation.deleted_at == None,
        )
        if not conv:
            return
        fb = CopilotFeedback.UP if feedback == "up" else CopilotFeedback.DOWN
        for m in conv.messages:
            if m.message_id == message_id:
                m.feedback = fb
                break
        conv.updated_at = datetime.now(timezone.utc)
        await conv.save()

    async def history(self, workspace_id: str, user_id: PydanticObjectId) -> CopilotHistoryResponse:
        await require_workspace_member(workspace_id, user_id)
        conv = await CopilotConversation.find_one(
            CopilotConversation.workspace_id == PydanticObjectId(workspace_id),
            CopilotConversation.user_id == user_id,
            CopilotConversation.deleted_at == None,
        )
        if not conv:
            return CopilotHistoryResponse(messages=[], total=0)
        messages = [
            CopilotMessageResponse(
                message_id=m.message_id or str(i),
                role=m.role.value,
                content=m.content,
                timestamp=m.timestamp,
            )
            for i, m in enumerate(conv.messages)
        ]
        return CopilotHistoryResponse(messages=messages, total=len(messages))


copilot_service = CopilotService()
