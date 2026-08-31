from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.repositories import notification as notification_repository
from app.repositories import reminder as reminder_repository
from app.schemas.notification import NotificationResponse
from app.services.notification import build_notification_message


REMINDER_WINDOW = timedelta(minutes=60)


async def send_event_reminder_batch(
    session: AsyncSession,
    event_id: UUID,
) -> list[NotificationResponse]:
    """Atomically create one due Event's reminder Notification batch."""

    notifications = []

    async with session.begin():
        current_time = datetime.now(timezone.utc)
        event = await reminder_repository.get_due_event_for_update(
            session,
            event_id,
            current_time=current_time,
            due_before=current_time + REMINDER_WINDOW,
        )
        if event is None:
            return []

        booking_contexts = (
            await reminder_repository.list_confirmed_booking_contexts(
                session,
                event.id,
            )
        )

        for booking_id, user_id in booking_contexts:
            notifications.append(
                notification_repository.add_notification(
                    session,
                    user_id=user_id,
                    notification_type=NotificationType.EVENT_REMINDER,
                    message=build_notification_message(
                        NotificationType.EVENT_REMINDER,
                        event.title,
                    ),
                    related_booking_id=booking_id,
                    related_review_id=None,
                )
            )

        reminder_repository.mark_reminder_sent(
            event,
            sent_at=current_time,
        )
        await session.flush()

        responses = [
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ]

    return responses
