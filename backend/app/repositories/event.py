from collections.abc import Collection, Mapping
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import EventStatus
from app.models.event import Category, Event, EventTag, Tag


_EDITABLE_EVENT_FIELDS = frozenset(
    {
        "title",
        "description",
        "venue",
        "event_datetime",
        "ticket_price",
        "total_tickets",
        "category_id",
        "status",
    }
)
_EVENTS_PER_PAGE = 6


def _visible_event_conditions(
    *,
    category_id: UUID | None,
    tag_ids: Collection[UUID],
) -> tuple[ColumnElement[bool], ...]:
    conditions: list[ColumnElement[bool]] = [
        Event.status == EventStatus.PUBLISHED,
        Event.deleted_at.is_(None),
        Event.event_datetime > func.now(),
    ]

    if category_id is not None:
        conditions.append(Event.category_id == category_id)

    conditions.extend(
        Event.event_tags.any(EventTag.tag_id == tag_id)
        for tag_id in tag_ids
    )
    return tuple(conditions)


async def count_visible_events(
    session: AsyncSession,
    *,
    category_id: UUID | None,
    tag_ids: Collection[UUID],
) -> int:
    statement = select(func.count(Event.id)).where(
        *_visible_event_conditions(
            category_id=category_id,
            tag_ids=tag_ids,
        )
    )
    return int(await session.scalar(statement) or 0)


async def list_visible_events(
    session: AsyncSession,
    *,
    page: int,
    category_id: UUID | None,
    tag_ids: Collection[UUID],
) -> list[Event]:
    statement = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.tags),
        )
        .where(
            *_visible_event_conditions(
                category_id=category_id,
                tag_ids=tag_ids,
            )
        )
        .order_by(Event.event_datetime, Event.id)
        .offset((page - 1) * _EVENTS_PER_PAGE)
        .limit(_EVENTS_PER_PAGE)
    )
    events = await session.scalars(statement)
    return list(events.all())


async def get_published_event_availability(
    session: AsyncSession,
    event_id: UUID,
) -> tuple[UUID, int, int] | None:
    statement = select(
        Event.id,
        Event.total_tickets,
        Event.tickets_available,
    ).where(
        Event.id == event_id,
        *_visible_event_conditions(
            category_id=None,
            tag_ids=(),
        ),
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return row.id, row.total_tickets, row.tickets_available


async def get_event_for_update(
    session: AsyncSession,
    event_id: UUID,
) -> Event | None:
    statement = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.event_tags),
            selectinload(Event.tags),
        )
        .where(
            Event.id == event_id,
            Event.deleted_at.is_(None),
        )
        .with_for_update()
    )
    return await session.scalar(statement)


async def get_event_for_cancellation_for_update(
    session: AsyncSession,
    event_id: UUID,
) -> Event | None:
    statement = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.event_tags),
            selectinload(Event.tags),
        )
        .where(Event.id == event_id)
        .with_for_update()
    )
    return await session.scalar(statement)


async def get_category_by_id(
    session: AsyncSession,
    category_id: UUID,
) -> Category | None:
    return await session.get(Category, category_id)


async def get_tags_by_ids(
    session: AsyncSession,
    tag_ids: Collection[UUID],
) -> list[Tag]:
    if not tag_ids:
        return []

    statement = select(Tag).where(Tag.id.in_(tag_ids))
    result = await session.scalars(statement)
    return list(result.all())


def update_event(
    event: Event,
    *,
    changes: Mapping[str, object],
    tags: Collection[Tag] | None = None,
    tickets_available: int | None = None,
) -> Event:
    unsupported_fields = changes.keys() - _EDITABLE_EVENT_FIELDS
    if unsupported_fields:
        fields = ", ".join(sorted(unsupported_fields))
        raise ValueError(f"Unsupported Event update fields: {fields}.")

    for field, value in changes.items():
        setattr(event, field, value)

    if tickets_available is not None:
        event.tickets_available = tickets_available

    if tags is not None:
        event.event_tags = [EventTag(tag=tag) for tag in tags]

    return event


def cancel_event(
    event: Event,
    *,
    cancelled_at: datetime,
) -> Event:
    event.status = EventStatus.CANCELLED
    event.deleted_at = cancelled_at
    return event


async def flush_event(
    session: AsyncSession,
) -> None:
    await session.flush()


async def refresh_event(
    session: AsyncSession,
    event: Event,
) -> Event:
    await session.refresh(
        event,
        attribute_names=[
            "status",
            "deleted_at",
            "updated_at",
            "category",
            "event_tags",
            "tags",
        ],
    )
    return event


async def create_event(
    session: AsyncSession,
    *,
    organizer_id: UUID,
    category_id: UUID | None,
    title: str,
    description: str,
    venue: str,
    event_datetime: datetime,
    ticket_price: Decimal,
    total_tickets: int,
    tickets_available: int,
    status: EventStatus,
    tags: Collection[Tag],
) -> Event:
    event = Event(
        organizer_id=organizer_id,
        category_id=category_id,
        title=title,
        description=description,
        venue=venue,
        event_datetime=event_datetime,
        ticket_price=ticket_price,
        total_tickets=total_tickets,
        tickets_available=tickets_available,
        status=status,
        event_tags=[EventTag(tag=tag) for tag in tags],
    )
    session.add(event)

    await session.flush()
    await session.refresh(
        event,
        attribute_names=["created_at", "updated_at"],
    )
    return event
