import logging
from datetime import datetime, timezone

from app.database.session import async_session_factory
from app.realtime.manager import notification_connection_manager
from app.repositories import reminder as reminder_repository
from app.services.reminder import REMINDER_WINDOW, send_event_reminder_batch


logger = logging.getLogger(__name__)


async def send_due_event_reminders() -> None:
    """Find due Events, persist each batch, then attempt live delivery."""

    try:
        current_time = datetime.now(timezone.utc)
        async with async_session_factory() as discovery_session:
            event_ids = await reminder_repository.list_due_event_ids(
                discovery_session,
                current_time=current_time,
                due_before=current_time + REMINDER_WINDOW,
            )
    except Exception:
        logger.exception("Scheduled reminder discovery failed.")
        return

    for event_id in event_ids:
        try:
            async with async_session_factory() as session:
                notifications = await send_event_reminder_batch(
                    session,
                    event_id,
                )

            for notification in notifications:
                await notification_connection_manager.send_notification(
                    notification.user_id,
                    notification,
                )
        except Exception:
            logger.exception(
                "Scheduled reminder processing failed for Event %s.",
                event_id,
            )
