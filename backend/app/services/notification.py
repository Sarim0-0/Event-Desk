from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import NotificationContextFilter, NotificationType
from app.models.user import User
from app.repositories import notification as notification_repository
from app.schemas.notification import (
    NotificationResponse,
    NotificationsReadAllResponse,
)


_BOOKING_NOTIFICATION_TYPES = frozenset(
    {
        NotificationType.BOOKING_CONFIRMED,
        NotificationType.BOOKING_CANCELLED,
        NotificationType.EVENT_CANCELLED,
    }
)

_NOTIFICATION_MESSAGE_TEMPLATES = {
    NotificationType.BOOKING_CONFIRMED: (
        'Your booking for "{event_title}" has been confirmed.'
    ),
    NotificationType.BOOKING_CANCELLED: (
        'Your booking for "{event_title}" has been cancelled.'
    ),
    NotificationType.EVENT_CANCELLED: (
        'The event "{event_title}" has been cancelled.'
    ),
    NotificationType.EVENT_REVIEWED: (
        'Your event "{event_title}" has received a new review.'
    ),
    NotificationType.REVIEW_REPLIED: (
        'Your review for "{event_title}" has received a new reply.'
    ),
}


async def list_notifications(
    session: AsyncSession,
    current_user: User,
    context_filter: NotificationContextFilter = NotificationContextFilter.ALL,
) -> list[NotificationResponse]:
    """Return only Notifications belonging to the authenticated User."""

    notifications = await notification_repository.list_user_notifications(
        session,
        user_id=current_user.id,
        context_filter=context_filter,
    )
    return [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]


async def mark_notification_read(
    session: AsyncSession,
    current_user: User,
    notification_id: UUID,
) -> NotificationResponse:
    """Mark one owned Notification as read."""

    try:
        notification = (
            await notification_repository.get_user_notification_by_id(
                session,
                notification_id=notification_id,
                user_id=current_user.id,
            )
        )
        if notification is None:
            raise NotFoundError("The selected notification does not exist.")

        notification_repository.mark_notification_as_read(
            notification,
            read_at=datetime.now(timezone.utc),
        )
        await notification_repository.flush_notification(
            session,
            notification,
        )

        response = NotificationResponse.model_validate(notification)

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def mark_all_notifications_read(
    session: AsyncSession,
    current_user: User,
) -> NotificationsReadAllResponse:
    """Mark every unread Notification belonging to the User as read."""

    try:
        updated_count = (
            await notification_repository.mark_all_user_notifications_as_read(
                session,
                user_id=current_user.id,
                read_at=datetime.now(timezone.utc),
            )
        )

        response = NotificationsReadAllResponse(
            updated_count=updated_count,
        )

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def create_notification(
    session: AsyncSession,
    *,
    notification_type: NotificationType,
    related_booking_id: UUID | None = None,
    related_review_id: UUID | None = None,
) -> NotificationResponse:
    """Persist one trusted, server-created Notification."""

    try:
        user_id, event_title = await _resolve_notification_context(
            session,
            notification_type=notification_type,
            related_booking_id=related_booking_id,
            related_review_id=related_review_id,
        )

        notification = notification_repository.add_notification(
            session,
            user_id=user_id,
            notification_type=notification_type,
            message=_build_message(notification_type, event_title),
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


async def create_event_cancellation_notifications(
    session: AsyncSession,
    *,
    event_id: UUID,
) -> list[NotificationResponse]:
    """Persist one Event-cancelled Notification per distinct booked User."""

    try:
        booking_contexts = (
            await notification_repository.get_cancelled_event_booking_contexts(
                session,
                event_id,
            )
        )
        notifications = [
            notification_repository.add_notification(
                session,
                user_id=user_id,
                notification_type=NotificationType.EVENT_CANCELLED,
                message=_build_message(
                    NotificationType.EVENT_CANCELLED,
                    event_title,
                ),
                related_booking_id=booking_id,
                related_review_id=None,
            )
            for booking_id, user_id, event_title in booking_contexts
        ]

        for notification in notifications:
            await notification_repository.flush_notification(
                session,
                notification,
            )
            await notification_repository.refresh_notification(
                session,
                notification,
            )

        responses = [
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ]

        await session.commit()
        return responses
    except Exception:
        await session.rollback()
        raise


async def _resolve_notification_context(
    session: AsyncSession,
    *,
    notification_type: NotificationType,
    related_booking_id: UUID | None,
    related_review_id: UUID | None,
) -> tuple[UUID, str]:
    if notification_type in _BOOKING_NOTIFICATION_TYPES:
        booking_id = _require_booking_context(
            related_booking_id=related_booking_id,
            related_review_id=related_review_id,
        )
        context = (
            await notification_repository.get_booking_notification_context(
                session,
                booking_id,
            )
        )
        if context is None:
            raise NotFoundError("The notification Booking does not exist.")
        return context

    review_id = _require_review_context(
        related_booking_id=related_booking_id,
        related_review_id=related_review_id,
    )

    if notification_type is NotificationType.EVENT_REVIEWED:
        context = (
            await notification_repository.get_reviewed_event_notification_context(
                session,
                review_id,
            )
        )
    elif notification_type is NotificationType.REVIEW_REPLIED:
        context = (
            await notification_repository.get_review_author_notification_context(
                session,
                review_id,
            )
        )
    else:
        raise ValueError("Unsupported notification type.")

    if context is None:
        raise NotFoundError("The notification Review does not exist.")
    return context


def _build_message(
    notification_type: NotificationType,
    event_title: str,
) -> str:
    return _NOTIFICATION_MESSAGE_TEMPLATES[notification_type].format(
        event_title=event_title,
    )


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
