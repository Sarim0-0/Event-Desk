from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.api.dependencies import (
    CurrentWebSocketUserId,
    DatabaseSession,
    require_permission,
)
from app.core.permissions import VIEW_OWN_NOTIFICATIONS
from app.models.enums import NotificationContextFilter
from app.models.user import User
from app.realtime.manager import notification_connection_manager
from app.schemas.notification import (
    NotificationResponse,
    NotificationsReadAllResponse,
)
from app.services.notification import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)


router = APIRouter(tags=["Notifications"])


@router.get(
    "/notifications",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_200_OK,
    name="list_notifications",
)
async def list_notifications_endpoint(
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_OWN_NOTIFICATIONS)),
    ],
    session: DatabaseSession,
    context: NotificationContextFilter = NotificationContextFilter.ALL,
) -> list[NotificationResponse]:
    return await list_notifications(
        session,
        current_user,
        context,
    )


@router.patch(
    "/notifications/read-all",
    response_model=NotificationsReadAllResponse,
    status_code=status.HTTP_200_OK,
    name="mark_all_notifications_read",
)
async def mark_all_notifications_read_endpoint(
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_OWN_NOTIFICATIONS)),
    ],
    session: DatabaseSession,
) -> NotificationsReadAllResponse:
    return await mark_all_notifications_read(session, current_user)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    name="mark_notification_read",
)
async def mark_notification_read_endpoint(
    notification_id: UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_OWN_NOTIFICATIONS)),
    ],
    session: DatabaseSession,
) -> NotificationResponse:
    return await mark_notification_read(
        session,
        current_user,
        notification_id,
    )


@router.websocket("/ws/notifications", name="notification_websocket")
async def notification_websocket_endpoint(
    websocket: WebSocket,
    user_id: CurrentWebSocketUserId,
) -> None:
    await notification_connection_manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        notification_connection_manager.disconnect(user_id, websocket)
