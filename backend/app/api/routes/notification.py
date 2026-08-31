from uuid import UUID

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.api.dependencies import (
    CurrentUser,
    CurrentWebSocketUserId,
    DatabaseSession,
)
from app.database.session import async_session_factory
from app.models.enums import NotificationContextFilter
from app.realtime.manager import notification_connection_manager
from app.schemas.notification import (
    NotificationResponse,
    NotificationsReadAllResponse,
)
from app.services.notification import (
    list_notifications,
    list_unread_notifications,
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
    """Connect and replay unread Notifications to this socket only.

    Live delivery can overlap replay. Clients should deduplicate payloads using
    the stable Notification ID included in every response.
    """

    await notification_connection_manager.connect(user_id, websocket)

    try:
        async with async_session_factory() as session:
            unread_notifications = await list_unread_notifications(
                session,
                user_id,
            )

        for notification in unread_notifications:
            await notification_connection_manager.send_notification_to_connection(
                user_id,
                websocket,
                notification,
            )

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        notification_connection_manager.disconnect(user_id, websocket)
