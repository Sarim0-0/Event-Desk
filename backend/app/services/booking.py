from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CREATE_BOOKINGS
from app.models.enums import BookingStatus, EventStatus
from app.models.user import User
from app.repositories import booking as booking_repository
from app.repositories import rbac as rbac_repository
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.auth import AccountUnavailableError


class BookingCreationForbiddenError(Exception):
    pass


class BookingEventNotFoundError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("The selected event does not exist.")


class EventNotBookableError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("Only published events can be booked.")


class InvalidBookingQuantityError(Exception):
    pass


class InsufficientTicketsError(Exception):
    def __init__(self, *, requested: int, available: int) -> None:
        self.requested = requested
        self.available = available
        super().__init__("The event does not have enough available tickets.")


async def create_booking(
    session: AsyncSession,
    current_user: User,
    request: BookingCreate,
) -> BookingResponse:
    try:
        _ensure_account_is_available(current_user)

        can_create_bookings = await rbac_repository.role_has_permission(
            session,
            current_user.role_id,
            CREATE_BOOKINGS,
        )
        if not can_create_bookings:
            raise BookingCreationForbiddenError

        if request.quantity < 1:
            raise InvalidBookingQuantityError

        event = await booking_repository.get_event_for_booking_for_update(
            session,
            request.event_id,
        )
        if event is None:
            raise BookingEventNotFoundError(request.event_id)

        if event.status is not EventStatus.PUBLISHED:
            raise EventNotBookableError(event.id)

        if event.tickets_available < request.quantity:
            raise InsufficientTicketsError(
                requested=request.quantity,
                available=event.tickets_available,
            )

        event.tickets_available -= request.quantity

        booking = booking_repository.add_booking(
            session,
            user_id=current_user.id,
            event_id=event.id,
            quantity=request.quantity,
            status=BookingStatus.CONFIRMED,
            booked_at=datetime.now(timezone.utc),
        )
        await booking_repository.flush_booking(session, booking)
        await booking_repository.refresh_booking(session, booking)

        response = BookingResponse.model_validate(booking)

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise AccountUnavailableError
