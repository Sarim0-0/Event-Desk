from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.event import Event


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


async def flush_booking(
    session: AsyncSession,
    booking: Booking,
) -> None:
    await session.flush([booking])


async def refresh_booking(
    session: AsyncSession,
    booking: Booking,
) -> Booking:
    await session.refresh(
        booking,
        attribute_names=["id", "booked_at", "created_at", "updated_at"],
    )
    return booking
