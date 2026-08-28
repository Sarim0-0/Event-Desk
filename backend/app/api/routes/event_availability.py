from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.dependencies import require_websocket_permission
from app.core.permissions import VIEW_PUBLISHED_EVENTS
from app.realtime.event_availability import (
    event_availability_connection_manager,
)


router = APIRouter(tags=["Events"])

EventAvailabilityViewer = Annotated[
    UUID,
    Depends(require_websocket_permission(VIEW_PUBLISHED_EVENTS)),
]


@router.websocket("/ws/events", name="event_availability_websocket")
async def event_availability_websocket_endpoint(
    websocket: WebSocket,
    viewer_id: EventAvailabilityViewer,
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
