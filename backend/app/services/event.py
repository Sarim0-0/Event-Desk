from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import event as event_repository
from app.schemas.event import EventCreateRequest, EventResponse
from app.services.auth import AccountUnavailableError


class CategoryNotFoundError(Exception):
    def __init__(self, category_id: UUID) -> None:
        self.category_id = category_id
        super().__init__("The selected category does not exist.")


class TagsNotFoundError(Exception):
    def __init__(self, tag_ids: set[UUID]) -> None:
        self.tag_ids = frozenset(tag_ids)
        super().__init__("One or more selected tags do not exist.")


class EventNotFoundError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("The selected Event does not exist.")


class EventUpdateForbiddenError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("You do not have permission to edit this Event.")


class EventNotEditableError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("This Event can no longer be edited.")


class EmptyEventUpdateError(Exception):
    def __init__(self) -> None:
        super().__init__("At least one Event field must be supplied.")


class InvalidEventUpdateError(Exception):
    def __init__(self) -> None:
        super().__init__("The Event update information is invalid.")


class EventCapacityBelowSoldTicketsError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "The total ticket capacity cannot be lower than the number "
            "of tickets already sold."
        )


class EventUpdateTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The Event could not be updated.")


async def create_event(
    session: AsyncSession,
    current_user: User,
    request: EventCreateRequest,
) -> EventResponse:
    try:
        _ensure_account_is_available(current_user)

        if request.category_id is not None:
            category = await event_repository.get_category_by_id(
                session,
                request.category_id,
            )
            if category is None:
                raise CategoryNotFoundError(request.category_id)

        tags = await event_repository.get_tags_by_ids(
            session,
            request.tag_ids,
        )
        found_tag_ids = {tag.id for tag in tags}
        missing_tag_ids = set(request.tag_ids) - found_tag_ids
        if missing_tag_ids:
            raise TagsNotFoundError(missing_tag_ids)

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


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise AccountUnavailableError
