from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event import Event
from app.models.review import Review


_BOOKINGS_PER_PAGE = 5


async def count_bookings_by_user(
    session: AsyncSession,
    user_id: UUID,
) -> int:
    statement = select(func.count(Booking.id)).where(
        Booking.user_id == user_id,
    )
    return int(await session.scalar(statement) or 0)


async def list_bookings_by_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    page: int,
) -> list[Booking]:
    statement = (
        select(Booking)
        .options(
            selectinload(Booking.event).selectinload(Event.organizer),
            selectinload(Booking.review).selectinload(Review.replies),
        )
        .where(Booking.user_id == user_id)
        .order_by(Booking.booked_at.desc(), Booking.id.desc())
        .offset((page - 1) * _BOOKINGS_PER_PAGE)
        .limit(_BOOKINGS_PER_PAGE)
    )
    bookings = await session.scalars(statement)
    return list(bookings.all())


async def get_user_booking_statuses_for_events(
    session: AsyncSession,
    *,
    user_id: UUID,
    event_ids: Collection[UUID],
) -> dict[UUID, BookingStatus]:
    """Return the current User's Booking status for the supplied Events."""

    if not event_ids:
        return {}

    statement = select(Booking.event_id, Booking.status).where(
        Booking.user_id == user_id,
        Booking.event_id.in_(event_ids),
    )
    rows = (await session.execute(statement)).all()
    return {row.event_id: row.status for row in rows}


async def list_bookings_for_organized_events(
    session: AsyncSession,
    *,
    organizer_id: UUID,
) -> list[Booking]:
    """Load Bookings belonging only to Events owned by one organizer."""

    statement = (
        select(Booking)
        .join(Booking.event)
        .options(
            joinedload(Booking.event),
            joinedload(Booking.user),
        )
        .where(Event.organizer_id == organizer_id)
        .order_by(
            Event.event_datetime.desc(),
            Event.id,
            Booking.booked_at.desc(),
            Booking.id.desc(),
        )
    )
    bookings = await session.scalars(statement)
    return list(bookings.unique().all())


async def get_event_for_booking_for_update(
    session: AsyncSession,
    event_id: UUID,
) -> Event | None:
    statement = (
        select(Event)
        .options(selectinload(Event.organizer))
        .where(
            Event.id == event_id,
            Event.deleted_at.is_(None),
        )
        .with_for_update()
    )
    return await session.scalar(statement)


async def get_booking_event_id(
    session: AsyncSession,
    booking_id: UUID,
) -> UUID | None:
    statement = select(Booking.event_id).where(
        Booking.id == booking_id,
    )
    return await session.scalar(statement)


async def get_booking_by_user_and_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    event_id: UUID,
) -> Booking | None:
    statement = select(Booking).where(
        Booking.user_id == user_id,
        Booking.event_id == event_id,
    )
    return await session.scalar(statement)


async def get_event_for_update(
    session: AsyncSession,
    event_id: UUID,
) -> Event | None:
    statement = (
        select(Event)
        .options(selectinload(Event.organizer))
        .where(Event.id == event_id)
        .with_for_update()
    )
    return await session.scalar(statement)


async def get_booking_for_update(
    session: AsyncSession,
    booking_id: UUID,
) -> Booking | None:
    statement = (
        select(Booking)
        .options(
            selectinload(Booking.review).selectinload(Review.replies)
        )
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    return await session.scalar(statement)


def add_booking(
    session: AsyncSession,
    *,
    user_id: UUID,
    event_id: UUID,
    quantity: int,
    status: BookingStatus,
    booked_at: datetime,
) -> Booking:
    booking = Booking(
        user_id=user_id,
        event_id=event_id,
        quantity=quantity,
        status=status,
        booked_at=booked_at,
    )
    session.add(booking)
    return booking


async def refresh_booking(
    session: AsyncSession,
    booking: Booking,
) -> Booking:
    await session.refresh(
        booking,
        attribute_names=["id", "booked_at", "created_at", "updated_at"],
    )
    return booking
