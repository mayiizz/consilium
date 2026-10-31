from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications", response_model=NotificationListResponse)
async def list_notifications(user: User = Depends(get_current_user)) -> NotificationListResponse:
    return await notification_service.list_for_user(user.id)


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str, user: User = Depends(get_current_user)
) -> NotificationResponse:
    return await notification_service.mark_read(notification_id, user.id)


@router.post("/api/notifications/read-all", response_model=MessageResponse)
async def mark_all_notifications_read(user: User = Depends(get_current_user)) -> MessageResponse:
    count = await notification_service.mark_all_read(user.id)
    return MessageResponse(message=f"Marked {count} notification(s) as read")
