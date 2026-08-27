"""In-memory WebSocket connections for the current single-process app.

Multiple application workers would need shared pub/sub, such as Redis, so a
notification received by one worker can reach connections held by another.
"""

import logging
from uuid import UUID

from fastapi import WebSocket

from app.schemas.notification import NotificationResponse


logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        user_connections = self._connections.get(user_id)
        if user_connections is None:
            return

        user_connections.discard(websocket)
        if not user_connections:
            self._connections.pop(user_id, None)

    async def send_notification(
        self,
        user_id: UUID,
        notification: NotificationResponse,
    ) -> None:
        connections = tuple(self._connections.get(user_id, ()))
        if not connections:
            return

        payload = {
            "type": "notification",
            "data": notification.model_dump(mode="json"),
        }

        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(user_id, websocket)
                logger.exception(
                    "Removed a failed Notification WebSocket connection."
                )


notification_connection_manager = NotificationConnectionManager()
