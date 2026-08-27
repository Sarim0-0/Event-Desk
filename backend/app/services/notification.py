from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import NotificationType
from app.repositories import notification as notification_repository
from app.schemas.notification import NotificationResponse


_BOOKING_NOTIFICATION_TYPES = frozenset(
    {
        NotificationType.BOOKING_CONFIRMED,
        NotificationType.BOOKING_CANCELLED,
        NotificationType.EVENT_CANCELLED,
    }
)

_NOTIFICATION_MESSAGES = {
    NotificationType.BOOKING_CONFIRMED: "Your booking has been confirmed.",
    NotificationType.BOOKING_CANCELLED: "Your booking has been cancelled.",
    NotificationType.EVENT_CANCELLED: "An event you booked has been cancelled.",
    NotificationType.EVENT_REVIEWED: "Your event has received a new review.",
    NotificationType.REVIEW_REPLIED: "Your review has received a new reply.",
}


async def create_notification(
    session: AsyncSession,
    *,
    notification_type: NotificationType,
    related_booking_id: UUID | None = None,
    related_review_id: UUID | None = None,
) -> NotificationResponse:
    """Persist one trusted, server-created Notification."""

    try:
        user_id = await _resolve_recipient_id(
            session,
            notification_type=notification_type,
            related_booking_id=related_booking_id,
            related_review_id=related_review_id,
        )

        notification = notification_repository.add_notification(
            session,
            user_id=user_id,
            notification_type=notification_type,
            message=_NOTIFICATION_MESSAGES[notification_type],
            related_booking_id=related_booking_id,
            related_review_id=related_review_id,
        )
        await notification_repository.flush_notification(
            session,
            notification,
        )
        await notification_repository.refresh_notification(
            session,
            notification,
        )

        response = NotificationResponse.model_validate(notification)

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def _resolve_recipient_id(
    session: AsyncSession,
    *,
    notification_type: NotificationType,
    related_booking_id: UUID | None,
    related_review_id: UUID | None,
) -> UUID:
    if notification_type in _BOOKING_NOTIFICATION_TYPES:
        booking_id = _require_booking_context(
            related_booking_id=related_booking_id,
            related_review_id=related_review_id,
        )
        user_id = await notification_repository.get_booking_owner_id(
            session,
            booking_id,
        )
        if user_id is None:
            raise NotFoundError("The notification Booking does not exist.")
        return user_id

    review_id = _require_review_context(
        related_booking_id=related_booking_id,
        related_review_id=related_review_id,
    )

    if notification_type is NotificationType.EVENT_REVIEWED:
        user_id = (
            await notification_repository.get_reviewed_event_organizer_id(
                session,
                review_id,
            )
        )
    elif notification_type is NotificationType.REVIEW_REPLIED:
        user_id = await notification_repository.get_review_author_id(
            session,
            review_id,
        )
    else:
        raise ValueError("Unsupported notification type.")

    if user_id is None:
        raise NotFoundError("The notification Review does not exist.")
    return user_id


def _require_booking_context(
    *,
    related_booking_id: UUID | None,
    related_review_id: UUID | None,
) -> UUID:
    if related_booking_id is None or related_review_id is not None:
        raise ValueError(
            "This notification type requires only a Booking context."
        )
    return related_booking_id


def _require_review_context(
    *,
    related_booking_id: UUID | None,
    related_review_id: UUID | None,
) -> UUID:
    if related_review_id is None or related_booking_id is not None:
        raise ValueError(
            "This notification type requires only a Review context."
        )
    return related_review_id
