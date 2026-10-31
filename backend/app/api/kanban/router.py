from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.kanban import KanbanReviewActionResponse, KanbanReviewListResponse
from app.services.kanban_review_service import kanban_review_service

router = APIRouter(tags=["kanban"])


@router.get(
    "/api/workspaces/{workspace_id}/kanban/review-queue",
    response_model=KanbanReviewListResponse,
)
async def list_kanban_review_queue(
    workspace_id: str, user: User = Depends(get_current_user)
) -> KanbanReviewListResponse:
    return await kanban_review_service.list_queue(workspace_id, user.id)


@router.post(
    "/api/workspaces/{workspace_id}/kanban/review-queue/{review_id}/approve",
    response_model=KanbanReviewActionResponse,
)
async def approve_kanban_review(
    workspace_id: str, review_id: str, user: User = Depends(get_current_user)
) -> KanbanReviewActionResponse:
    return await kanban_review_service.approve(workspace_id, user.id, review_id)


@router.post(
    "/api/workspaces/{workspace_id}/kanban/review-queue/{review_id}/reject",
    response_model=KanbanReviewActionResponse,
)
async def reject_kanban_review(
    workspace_id: str, review_id: str, user: User = Depends(get_current_user)
) -> KanbanReviewActionResponse:
    return await kanban_review_service.reject(workspace_id, user.id, review_id)
