from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import NotificationType
from app.models.event import Event
from app.models.notification import Notification
from app.models.review import Review


async def get_booking_owner_id(
    session: AsyncSession,
    booking_id: UUID,
) -> UUID | None:
    statement = select(Booking.user_id).where(Booking.id == booking_id)
    return await session.scalar(statement)


async def get_review_author_id(
    session: AsyncSession,
    review_id: UUID,
) -> UUID | None:
    statement = (
        select(Booking.user_id)
        .join(Review, Review.booking_id == Booking.id)
        .where(Review.id == review_id)
    )
    return await session.scalar(statement)


async def get_reviewed_event_organizer_id(
    session: AsyncSession,
    review_id: UUID,
) -> UUID | None:
    statement = (
        select(Event.organizer_id)
        .join(Booking, Booking.event_id == Event.id)
        .join(Review, Review.booking_id == Booking.id)
        .where(Review.id == review_id)
    )
    return await session.scalar(statement)


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
