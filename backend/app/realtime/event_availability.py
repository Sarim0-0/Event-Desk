"""In-memory connections for public Event availability updates.

This manager is suitable for the current single-process application. Multiple
application workers would require shared pub/sub, such as Redis, so every
worker receives the same availability updates.
"""

import logging

from fastapi import WebSocket

from app.schemas.event import EventAvailabilityResponse


logger = logging.getLogger(__name__)


class EventAvailabilityConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_availability(
        self,
        availability: EventAvailabilityResponse,
    ) -> None:
        payload = {
            "type": "event_availability_updated",
            "data": availability.model_dump(mode="json"),
        }

        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)
                logger.exception(
                    "Removed a failed Event availability WebSocket connection."
                )


event_availability_connection_manager = (
    EventAvailabilityConnectionManager()
)
