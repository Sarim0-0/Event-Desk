import logging
from uuid import UUID

from app.database.session import async_session_factory
from app.realtime.event_availability import (
    event_availability_connection_manager,
)
from app.services.event import get_event_availability


logger = logging.getLogger(__name__)


async def broadcast_event_availability_in_background(
    *,
    event_id: UUID,
) -> None:
    """Load committed Event inventory and broadcast it to current viewers."""

    try:
        async with async_session_factory() as session:
            availability = await get_event_availability(session, event_id)

        if availability is None:
            return

        await event_availability_connection_manager.broadcast_availability(
            availability
        )
    except Exception:
        logger.exception(
            "Background Event availability broadcast failed for Event %s.",
            event_id,
        )
