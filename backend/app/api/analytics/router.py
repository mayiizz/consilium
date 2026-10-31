from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import AnalyticsResponse, DashboardResponse, RisksResponse, RoadmapResponse
from app.services.analytics_service import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/api/workspaces/{workspace_id}/dashboard", response_model=DashboardResponse)
async def dashboard(
    workspace_id: str, user: User = Depends(get_current_user)
) -> DashboardResponse:
    return await analytics_service.dashboard(workspace_id, user.id)


@router.get("/api/workspaces/{workspace_id}/analytics", response_model=AnalyticsResponse)
async def analytics(
    workspace_id: str, user: User = Depends(get_current_user)
) -> AnalyticsResponse:
    return await analytics_service.analytics(workspace_id, user.id)


@router.get("/api/workspaces/{workspace_id}/roadmap", response_model=RoadmapResponse)
async def roadmap(
    workspace_id: str, user: User = Depends(get_current_user)
) -> RoadmapResponse:
    return await analytics_service.roadmap(workspace_id, user.id)


@router.get("/api/workspaces/{workspace_id}/risks", response_model=RisksResponse)
async def risks(
    workspace_id: str, user: User = Depends(get_current_user)
) -> RisksResponse:
    return await analytics_service.risks(workspace_id, user.id)
