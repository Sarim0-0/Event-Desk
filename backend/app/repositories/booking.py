from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event import Event


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
        .options(selectinload(Booking.event))
        .where(Booking.user_id == user_id)
        .order_by(Booking.booked_at.desc(), Booking.id.desc())
        .offset((page - 1) * _BOOKINGS_PER_PAGE)
        .limit(_BOOKINGS_PER_PAGE)
    )
    bookings = await session.scalars(statement)
    return list(bookings.all())


async def get_event_for_booking_for_update(
    session: AsyncSession,
    event_id: UUID,
) -> Event | None:
    statement = (
        select(Event)
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
