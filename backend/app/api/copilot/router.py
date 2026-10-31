from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import (
    CopilotChatRequest,
    CopilotFeedbackRequest,
    CopilotHistoryResponse,
    CopilotMessageResponse,
    MessageResponse,
)
from app.services.copilot_service import copilot_service

router = APIRouter(tags=["copilot"])


@router.post(
    "/api/workspaces/{workspace_id}/copilot/chat",
    response_model=CopilotMessageResponse,
)
async def copilot_chat(
    workspace_id: str,
    data: CopilotChatRequest,
    user: User = Depends(get_current_user),
) -> CopilotMessageResponse:
    return await copilot_service.chat(workspace_id, user.id, data)


@router.post("/api/copilot/feedback", response_model=MessageResponse)
async def copilot_feedback(
    data: CopilotFeedbackRequest, user: User = Depends(get_current_user)
) -> MessageResponse:
    await copilot_service.feedback(data.workspace_id, user.id, data.message_id, data.feedback)
    return MessageResponse(message="Feedback recorded")


@router.get(
    "/api/workspaces/{workspace_id}/copilot/history",
    response_model=CopilotHistoryResponse,
)
async def copilot_history(
    workspace_id: str, user: User = Depends(get_current_user)
) -> CopilotHistoryResponse:
    return await copilot_service.history(workspace_id, user.id)
