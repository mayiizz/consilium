from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import (
    CreateResearchRequest,
    ResearchJobListResponse,
    ResearchJobResponse,
)
from app.schemas.research_chat import (
    ResearchChatHistoryResponse,
    ResearchChatRequest,
    ResearchChatResponse,
)
from app.services.research_agent_service import research_agent_service
from app.services.research_chat_service import research_chat_service

router = APIRouter(tags=["research"])


@router.post(
    "/api/workspaces/{workspace_id}/research/chat",
    response_model=ResearchChatResponse,
)
async def research_chat(
    workspace_id: str,
    data: ResearchChatRequest,
    user: User = Depends(get_current_user),
) -> ResearchChatResponse:
    return await research_chat_service.chat(workspace_id, user.id, data)


@router.get(
    "/api/workspaces/{workspace_id}/research/chat/history",
    response_model=ResearchChatHistoryResponse,
)
async def research_chat_history(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> ResearchChatHistoryResponse:
    return await research_chat_service.history(workspace_id, user.id)


@router.post("/api/workspaces/{workspace_id}/research/chat/clear")
async def research_chat_clear(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    return await research_chat_service.clear(workspace_id, user.id)


@router.post(
    "/api/workspaces/{workspace_id}/research",
    response_model=ResearchJobResponse,
)
async def create_research(
    workspace_id: str,
    data: CreateResearchRequest,
    user: User = Depends(get_current_user),
) -> ResearchJobResponse:
    return await research_agent_service.create_job(workspace_id, user.id, data)


@router.get(
    "/api/workspaces/{workspace_id}/research",
    response_model=ResearchJobListResponse,
)
async def list_research(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> ResearchJobListResponse:
    return await research_agent_service.list_jobs(workspace_id, user.id)


@router.get(
    "/api/workspaces/{workspace_id}/research/{job_id}",
    response_model=ResearchJobResponse,
)
async def get_research(
    workspace_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
) -> ResearchJobResponse:
    return await research_agent_service.get_job(workspace_id, job_id, user.id)


@router.post(
    "/api/workspaces/{workspace_id}/research/{job_id}/retry",
    response_model=ResearchJobResponse,
)
async def retry_research(
    workspace_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
) -> ResearchJobResponse:
    return await research_agent_service.retry_job(workspace_id, job_id, user.id)


@router.get("/api/workspaces/{workspace_id}/research/{job_id}/export")
async def export_research(
    workspace_id: str,
    job_id: str,
    format: str = "md",
    user: User = Depends(get_current_user),
) -> Response:
    body, mime, filename = await research_agent_service.export_job(
        workspace_id, job_id, user.id, format
    )
    return Response(
        content=body,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
