import logging
from uuid import UUID

from app.database.session import async_session_factory
from app.models.enums import NotificationType
from app.realtime.manager import notification_connection_manager
from app.services.notification import (
    create_event_cancellation_notifications,
    create_notification,
)


logger = logging.getLogger(__name__)


async def create_notification_in_background(
    *,
    notification_type: NotificationType,
    related_booking_id: UUID | None = None,
    related_review_id: UUID | None = None,
) -> None:
    """Persist a Notification using a session owned by this background task."""

    try:
        async with async_session_factory() as session:
            notification = await create_notification(
                session,
                notification_type=notification_type,
                related_booking_id=related_booking_id,
                related_review_id=related_review_id,
            )

        await notification_connection_manager.send_notification(
            notification.user_id,
            notification,
        )
    except Exception:
        logger.exception(
            "Background notification processing failed for type %s.",
            notification_type.value,
        )


async def create_event_cancellation_notifications_in_background(
    *,
    event_id: UUID,
) -> None:
    """Persist and deliver the distinct Event-cancellation Notifications."""

    try:
        async with async_session_factory() as session:
            notifications = await create_event_cancellation_notifications(
                session,
                event_id=event_id,
            )

        for notification in notifications:
            await notification_connection_manager.send_notification(
                notification.user_id,
                notification,
            )
    except Exception:
        logger.exception(
            "Background Event-cancellation notification processing failed."
        )
