from collections.abc import Collection
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventStatus
from app.models.event import Category, Event, EventTag, Tag


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
