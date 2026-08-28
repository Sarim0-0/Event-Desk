from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import BookingStatus, EventStatus, NotificationType
from app.models.event import Event
from app.models.notification import Notification
from app.models.review import Review


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


async def flush_notification(
    session: AsyncSession,
    notification: Notification,
) -> None:
    await session.flush([notification])


async def refresh_notification(
    session: AsyncSession,
    notification: Notification,
) -> Notification:
    await session.refresh(
        notification,
        attribute_names=["id", "created_at"],
    )
    return notification
