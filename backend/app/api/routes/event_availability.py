from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import CurrentWebSocketUserId
from app.realtime.event_availability import (
    event_availability_connection_manager,
)


router = APIRouter(tags=["Events"])


@router.websocket("/ws/events", name="event_availability_websocket")
async def event_availability_websocket_endpoint(
    websocket: WebSocket,
    _viewer_id: CurrentWebSocketUserId,
) -> None:
    """Keep one authenticated connection open for Event availability."""

    await event_availability_connection_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        event_availability_connection_manager.disconnect(websocket)
