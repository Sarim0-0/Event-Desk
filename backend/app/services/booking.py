from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CANCEL_ANY_BOOKING,
    CANCEL_OWN_BOOKING,
    CREATE_BOOKINGS,
)
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


class BookingNotFoundError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("The selected booking does not exist.")


class BookingAlreadyCancelledError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("The booking has already been cancelled.")


class BookingNotConfirmedError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("Only a confirmed booking can be cancelled.")


class BookingCancellationForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("You do not have permission to cancel this booking.")


class BookingCancellationEventNotFoundError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("The event for this booking does not exist.")


class BookingInventoryConflictError(Exception):
    def __init__(self, *, available_after_restoration: int, total: int) -> None:
        self.available_after_restoration = available_after_restoration
        self.total = total
        super().__init__("Cancelling this booking would make ticket inventory invalid.")


class BookingCancellationTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The booking cancellation could not be completed.")


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


async def cancel_booking(
    session: AsyncSession,
    current_user: User,
    booking_id: UUID,
) -> BookingResponse:
    try:
        _ensure_account_is_available(current_user)

        event_id = await booking_repository.get_booking_event_id(
            session,
            booking_id,
        )
        if event_id is None:
            raise BookingNotFoundError(booking_id)

        event = await booking_repository.get_event_for_update(
            session,
            event_id,
        )
        if event is None:
            raise BookingCancellationEventNotFoundError(event_id)

        booking = await booking_repository.get_booking_for_update(
            session,
            booking_id,
        )
        if booking is None or booking.deleted_at is not None:
            raise BookingNotFoundError(booking_id)

        if booking.event_id != event_id:
            raise BookingCancellationTransactionError()

        if booking.status is BookingStatus.CANCELLED:
            raise BookingAlreadyCancelledError(booking.id)
        if booking.status is not BookingStatus.CONFIRMED:
            raise BookingNotConfirmedError(booking.id)

        can_cancel_any_booking = await rbac_repository.role_has_permission(
            session,
            current_user.role_id,
            CANCEL_ANY_BOOKING,
        )
        if not can_cancel_any_booking:
            can_cancel_own_booking = await rbac_repository.role_has_permission(
                session,
                current_user.role_id,
                CANCEL_OWN_BOOKING,
            )
            if (
                not can_cancel_own_booking
                or booking.user_id != current_user.id
            ):
                raise BookingCancellationForbiddenError()

        available_after_restoration = (
            event.tickets_available + booking.quantity
        )
        if not 0 <= available_after_restoration <= event.total_tickets:
            raise BookingInventoryConflictError(
                available_after_restoration=available_after_restoration,
                total=event.total_tickets,
            )

        event.tickets_available = available_after_restoration
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)

        await booking_repository.flush_booking(session, booking)
        await booking_repository.refresh_booking(session, booking)

        response = BookingResponse.model_validate(booking)

        await session.commit()
        return response
    except SQLAlchemyError as error:
        await session.rollback()
        raise BookingCancellationTransactionError() from error
    except Exception:
        await session.rollback()
        raise


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise AccountUnavailableError
