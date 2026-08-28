from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import EventStatus
from app.models.event import Tag
from app.models.user import User
from app.repositories import event as event_repository
from app.schemas.event import (
    EVENTS_PER_PAGE,
    EventCreateRequest,
    EventListQuery,
    EventResponse,
    EventUpdate,
    PaginatedEventsResponse,
)


async def list_events(
    session: AsyncSession,
    query: EventListQuery,
) -> PaginatedEventsResponse:
    """Return one read-only page of visible, filtered Events."""

    total_items = await event_repository.count_visible_events(
        session,
        category_id=query.category_id,
        tag_ids=query.tag_ids,
    )
    events = await event_repository.list_visible_events(
        session,
        page=query.page,
        category_id=query.category_id,
        tag_ids=query.tag_ids,
    )

    items = [
        EventResponse(
            id=event.id,
            organizer_id=event.organizer_id,
            title=event.title,
            description=event.description,
            venue=event.venue,
            event_datetime=event.event_datetime,
            ticket_price=event.ticket_price,
            total_tickets=event.total_tickets,
            tickets_available=event.tickets_available,
            category_id=event.category_id,
            tag_ids=[tag.id for tag in event.tags],
            status=event.status,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        for event in events
    ]
    total_pages = (total_items + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE

    return PaginatedEventsResponse(
        items=items,
        page=query.page,
        total_items=total_items,
        total_pages=total_pages,
    )


async def create_event(
    session: AsyncSession,
    current_user: User,
    request: EventCreateRequest,
) -> EventResponse:
    try:
        if request.category_id is not None:
            category = await event_repository.get_category_by_id(
                session,
                request.category_id,
            )
            if category is None:
                raise NotFoundError("The selected category does not exist.")

        tags = await event_repository.get_tags_by_ids(
            session,
            request.tag_ids,
        )
        found_tag_ids = {tag.id for tag in tags}
        missing_tag_ids = set(request.tag_ids) - found_tag_ids
        if missing_tag_ids:
            raise NotFoundError("One or more selected tags do not exist.")

        event = await event_repository.create_event(
            session,
            organizer_id=current_user.id,
            category_id=request.category_id,
            title=request.title,
            description=request.description,
            venue=request.venue,
            event_datetime=request.event_datetime,
            ticket_price=request.ticket_price,
            total_tickets=request.total_tickets,
            tickets_available=request.total_tickets,
            status=request.status,
            tags=tags,
        )

        response = EventResponse(
            id=event.id,
            organizer_id=event.organizer_id,
            title=event.title,
            description=event.description,
            venue=event.venue,
            event_datetime=event.event_datetime,
            ticket_price=event.ticket_price,
            total_tickets=event.total_tickets,
            tickets_available=event.tickets_available,
            category_id=event.category_id,
            tag_ids=request.tag_ids,
            status=event.status,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def update_event(
    session: AsyncSession,
    current_user: User,
    event_id: UUID,
    request: EventUpdate,
    *,
    can_edit_own: bool,
    can_edit_any: bool,
) -> EventResponse:
    try:
        changes = request.model_dump(exclude_unset=True)

        event = await event_repository.get_event_for_update(session, event_id)
        if event is None:
            raise NotFoundError("The selected Event does not exist.")

        if event.deleted_at is not None or event.status in {
            EventStatus.CANCELLED,
            EventStatus.COMPLETED,
        }:
            raise ConflictError("This Event can no longer be edited.")

        if not can_edit_any and (
            not can_edit_own
            or event.organizer_id != current_user.id
        ):
            raise ForbiddenError(
                "You do not have permission to edit this Event."
            )

        category_id = cast(UUID | None, changes.get("category_id"))
        if "category_id" in changes and category_id is not None:
            category = await event_repository.get_category_by_id(
                session,
                category_id,
            )
            if category is None:
                raise NotFoundError("The selected category does not exist.")

        tags: list[Tag] | None = None
        if "tag_ids" in changes:
            tag_ids = cast(list[UUID], changes.pop("tag_ids"))
            tags = await event_repository.get_tags_by_ids(session, tag_ids)

            found_tag_ids = {tag.id for tag in tags}
            missing_tag_ids = set(tag_ids) - found_tag_ids
            if missing_tag_ids:
                raise NotFoundError(
                    "One or more selected tags do not exist."
                )

        tickets_available: int | None = None
        if "total_tickets" in changes:
            new_total_tickets = cast(int, changes["total_tickets"])
            tickets_sold = event.total_tickets - event.tickets_available
            if new_total_tickets < tickets_sold:
                raise ConflictError(
                    "The total ticket capacity cannot be lower than the "
                    "number of tickets already sold."
                )
            tickets_available = new_total_tickets - tickets_sold

        event_repository.update_event(
            event,
            changes=changes,
            tags=tags,
            tickets_available=tickets_available,
        )
        await event_repository.flush_event(session)
        await event_repository.refresh_event(session, event)

        response = EventResponse(
            id=event.id,
            organizer_id=event.organizer_id,
            title=event.title,
            description=event.description,
            venue=event.venue,
            event_datetime=event.event_datetime,
            ticket_price=event.ticket_price,
            total_tickets=event.total_tickets,
            tickets_available=event.tickets_available,
            category_id=event.category_id,
            tag_ids=[tag.id for tag in event.tags],
            status=event.status,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def cancel_event(
    session: AsyncSession,
    current_user: User,
    event_id: UUID,
    *,
    can_cancel_own: bool,
    can_cancel_any: bool,
) -> EventResponse:
    try:
        event = await event_repository.get_event_for_cancellation_for_update(
            session,
            event_id,
        )
        if event is None:
            raise NotFoundError("The selected Event does not exist.")

        if (
            event.status is EventStatus.CANCELLED
            or event.deleted_at is not None
        ):
            raise ConflictError("This Event has already been cancelled.")

        if event.status is EventStatus.COMPLETED:
            raise ConflictError("This Event can no longer be cancelled.")

        if not can_cancel_any and (
            not can_cancel_own
            or event.organizer_id != current_user.id
        ):
            raise ForbiddenError(
                "You do not have permission to cancel this Event."
            )

        event_repository.cancel_event(
            event,
            cancelled_at=datetime.now(timezone.utc),
        )
        await event_repository.flush_event(session)
        await event_repository.refresh_event(session, event)

        response = EventResponse(
            id=event.id,
            organizer_id=event.organizer_id,
            title=event.title,
            description=event.description,
            venue=event.venue,
            event_datetime=event.event_datetime,
            ticket_price=event.ticket_price,
            total_tickets=event.total_tickets,
            tickets_available=event.tickets_available,
            category_id=event.category_id,
            tag_ids=[tag.id for tag in event.tags],
            status=event.status,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise
