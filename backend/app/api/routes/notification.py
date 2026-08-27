from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import CurrentWebSocketUserId
from app.realtime.manager import notification_connection_manager


router = APIRouter(tags=["Notifications"])


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
