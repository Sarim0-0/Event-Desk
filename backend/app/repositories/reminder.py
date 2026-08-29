from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.booking import Booking
from app.models.enums import BookingStatus, EventStatus
from app.models.event import Event


def _due_event_conditions(
    *,
    current_time: datetime,
    due_before: datetime,
) -> tuple[ColumnElement[bool], ...]:
    return (
        Event.status == EventStatus.PUBLISHED,
        Event.deleted_at.is_(None),
        Event.reminder_sent_at.is_(None),
        Event.event_datetime > current_time,
        Event.event_datetime <= due_before,
    )


async def list_due_event_ids(
    session: AsyncSession,
    *,
    current_time: datetime,
    due_before: datetime,
) -> list[UUID]:
    """Find candidate Event IDs without keeping ORM objects or row locks."""

    statement = (
        select(Event.id)
        .where(
            *_due_event_conditions(
                current_time=current_time,
                due_before=due_before,
            )
        )
        .order_by(Event.event_datetime, Event.id)
    )
    event_ids = await session.scalars(statement)
    return list(event_ids.all())


async def get_due_event_for_update(
    session: AsyncSession,
    event_id: UUID,
    *,
    current_time: datetime,
    due_before: datetime,
) -> Event | None:
    """Lock and recheck one due Event before creating its reminder batch."""

    statement = (
        select(Event)
        .where(
            Event.id == event_id,
            *_due_event_conditions(
                current_time=current_time,
                due_before=due_before,
            ),
        )
        .with_for_update()
    )
    return await session.scalar(statement)


async def list_confirmed_booking_contexts(
    session: AsyncSession,
    event_id: UUID,
) -> list[tuple[UUID, UUID]]:
    """Return confirmed Booking IDs and their owners for one Event."""

    statement = (
        select(Booking.id, Booking.user_id)
        .where(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
        .order_by(Booking.id)
    )
    rows = (await session.execute(statement)).all()
    return [(row.id, row.user_id) for row in rows]


def mark_reminder_sent(
    event: Event,
    *,
    sent_at: datetime,
) -> Event:
    event.reminder_sent_at = sent_at
    return event


async def flush_reminder_batch(session: AsyncSession) -> None:
    """Flush the marker and all Notification inserts without committing."""

    await session.flush()
