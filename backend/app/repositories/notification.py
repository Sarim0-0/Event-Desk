from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import (
    BookingStatus,
    EventStatus,
    NotificationContextFilter,
    NotificationType,
)
from app.models.event import Event
from app.models.notification import Notification
from app.models.review import Review


async def list_user_notifications(
    session: AsyncSession,
    *,
    user_id: UUID,
    context_filter: NotificationContextFilter,
) -> list[Notification]:
    statement = select(Notification).where(Notification.user_id == user_id)

    if context_filter is NotificationContextFilter.BOOKING:
        statement = statement.where(
            Notification.related_booking_id.is_not(None)
        )
    elif context_filter is NotificationContextFilter.REVIEW:
        statement = statement.where(
            Notification.related_review_id.is_not(None)
        )

    statement = statement.order_by(
        Notification.created_at.desc(),
        Notification.id.desc(),
    )
    notifications = await session.scalars(statement)
    return list(notifications.all())


async def list_unread_user_notifications(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> list[Notification]:
    statement = (
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .order_by(
            Notification.created_at,
            Notification.id,
        )
    )
    notifications = await session.scalars(statement)
    return list(notifications.all())


async def get_user_notification_by_id(
    session: AsyncSession,
    *,
    notification_id: UUID,
    user_id: UUID,
) -> Notification | None:
    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    return await session.scalar(statement)


def mark_notification_as_read(
    notification: Notification,
    *,
    read_at: datetime,
) -> Notification:
    if notification.read_at is None:
        notification.read_at = read_at
    return notification


async def mark_all_user_notifications_as_read(
    session: AsyncSession,
    *,
    user_id: UUID,
    read_at: datetime,
) -> int:
    statement = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=read_at)
        .returning(Notification.id)
    )
    updated_ids = await session.scalars(statement)
    return len(updated_ids.all())


async def get_booking_notification_context(
    session: AsyncSession,
    booking_id: UUID,
) -> tuple[UUID, str] | None:
    statement = (
        select(
            Booking.user_id,
            Event.title.label("event_title"),
        )
        .join(Event, Booking.event_id == Event.id)
        .where(Booking.id == booking_id)
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return row.user_id, row.event_title


async def get_review_author_notification_context(
    session: AsyncSession,
    review_id: UUID,
) -> tuple[UUID, str] | None:
    statement = (
        select(
            Booking.user_id,
            Event.title.label("event_title"),
        )
        .join(Review, Review.booking_id == Booking.id)
        .join(Event, Booking.event_id == Event.id)
        .where(Review.id == review_id)
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return row.user_id, row.event_title


async def get_reviewed_event_notification_context(
    session: AsyncSession,
    review_id: UUID,
) -> tuple[UUID, str] | None:
    statement = (
        select(
            Event.organizer_id.label("user_id"),
            Event.title.label("event_title"),
        )
        .join(Booking, Booking.event_id == Event.id)
        .join(Review, Review.booking_id == Booking.id)
        .where(Review.id == review_id)
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return row.user_id, row.event_title


async def get_cancelled_event_booking_contexts(
    session: AsyncSession,
    event_id: UUID,
) -> list[tuple[UUID, UUID, str]]:
    """Return confirmed Booking contexts for a cancelled Event."""

    statement = (
        select(
            Booking.id,
            Booking.user_id,
            Event.title.label("event_title"),
        )
        .join(Event, Booking.event_id == Event.id)
        .where(
            Event.id == event_id,
            Event.status == EventStatus.CANCELLED,
            Event.deleted_at.is_not(None),
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    rows = (await session.execute(statement)).all()
    return [
        (row.id, row.user_id, row.event_title)
        for row in rows
    ]


async def get_cancelled_event_organizer_context(
    session: AsyncSession,
    event_id: UUID,
) -> tuple[UUID, str] | None:
    """Return the owner and title of an Event after it has been cancelled."""

    statement = select(
        Event.organizer_id,
        Event.title,
    ).where(
        Event.id == event_id,
        Event.status == EventStatus.CANCELLED,
        Event.deleted_at.is_not(None),
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return row.organizer_id, row.title


def add_notification(
    session: AsyncSession,
    *,
    user_id: UUID,
    notification_type: NotificationType,
    message: str,
    related_booking_id: UUID | None,
    related_review_id: UUID | None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type.value,
        message=message,
        related_booking_id=related_booking_id,
        related_review_id=related_review_id,
    )
    session.add(notification)
    return notification


async def refresh_notification(
    session: AsyncSession,
    notification: Notification,
) -> Notification:
    await session.refresh(
        notification,
        attribute_names=["id", "created_at"],
    )
    return notification
