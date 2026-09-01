from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import (
    AuditAction,
    AuditEntityType,
    BookingStatus,
    EventStatus,
)
from app.models.user import User
from app.models.booking import Booking
from app.models.event import Event
from app.models.review import Review
from app.repositories import booking as booking_repository
from app.repositories import user as user_repository
from app.schemas.booking import (
    BOOKINGS_PER_PAGE,
    BookingCreate,
    BookingListQuery,
    BookingResponse,
    PaginatedBookingsResponse,
)
from app.services import audit as audit_service


async def list_own_bookings(
    session: AsyncSession,
    current_user: User,
    query: BookingListQuery,
) -> PaginatedBookingsResponse:
    """Return one read-only page of the authenticated User's Bookings."""

    return await _list_bookings_for_user(
        session,
        user_id=current_user.id,
        query=query,
    )


async def list_user_bookings(
    session: AsyncSession,
    user_id: UUID,
    query: BookingListQuery,
) -> PaginatedBookingsResponse:
    """Return one booking page for an Admin-selected User."""

    target_user = await user_repository.get_user_by_id(session, user_id)
    if target_user is None:
        raise NotFoundError("The selected User does not exist.")

    return await _list_bookings_for_user(
        session,
        user_id=target_user.id,
        query=query,
    )


async def _list_bookings_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    query: BookingListQuery,
) -> PaginatedBookingsResponse:
    """Build the shared paginated Booking response for one User ID."""

    total_items = await booking_repository.count_bookings_by_user(
        session,
        user_id,
    )
    bookings = await booking_repository.list_bookings_by_user(
        session,
        user_id=user_id,
        page=query.page,
    )
    total_pages = (total_items + BOOKINGS_PER_PAGE - 1) // BOOKINGS_PER_PAGE

    return PaginatedBookingsResponse(
        items=[
            _booking_response(
                booking,
                booking.event,
                review=booking.review,
            )
            for booking in bookings
        ],
        page=query.page,
        total_items=total_items,
        total_pages=total_pages,
    )


async def create_booking(
    session: AsyncSession,
    current_user: User,
    request: BookingCreate,
) -> BookingResponse:
    try:
        event = await booking_repository.get_event_for_booking_for_update(
            session,
            request.event_id,
        )
        if event is None:
            raise NotFoundError("The selected event does not exist.")

        if (
            event.status is not EventStatus.PUBLISHED
            or event.event_datetime <= datetime.now(timezone.utc)
        ):
            raise ConflictError(
                "Only upcoming published events can be booked."
            )

        existing_booking = await booking_repository.get_booking_by_user_and_event(
            session,
            user_id=current_user.id,
            event_id=event.id,
        )
        if existing_booking is not None:
            raise ConflictError(
                "You already have a booking for this event."
            )

        if event.tickets_available < request.quantity:
            raise ConflictError(
                "The event does not have enough available tickets."
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
        await session.flush([booking])
        await booking_repository.refresh_booking(session, booking)

        audit_service.record_action(
            session,
            actor_id=current_user.id,
            action=AuditAction.BOOKING_CREATED,
            entity_type=AuditEntityType.BOOKING,
            entity_id=booking.id,
        )

        response = _booking_response(booking, event)

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        if _get_constraint_name(error) == "uq_bookings_user_id_event_id":
            raise ConflictError(
                "You already have a booking for this event."
            ) from error
        raise
    except Exception:
        await session.rollback()
        raise


async def cancel_booking(
    session: AsyncSession,
    current_user: User,
    booking_id: UUID,
    *,
    can_cancel_any: bool,
) -> BookingResponse:
    try:
        event_id = await booking_repository.get_booking_event_id(
            session,
            booking_id,
        )
        if event_id is None:
            raise NotFoundError("The selected booking does not exist.")

        event = await booking_repository.get_event_for_update(
            session,
            event_id,
        )
        if event is None:
            raise RuntimeError("The booking references a missing event.")

        booking = await booking_repository.get_booking_for_update(
            session,
            booking_id,
        )
        if booking is None:
            raise NotFoundError("The selected booking does not exist.")

        if booking.event_id != event_id:
            raise RuntimeError("The booking event changed during cancellation.")

        if booking.status is BookingStatus.CANCELLED:
            raise ConflictError("The booking has already been cancelled.")

        if not can_cancel_any and booking.user_id != current_user.id:
            raise ForbiddenError(
                "You do not have permission to cancel this booking."
            )

        if event.status is EventStatus.CANCELLED:
            raise ConflictError(
                "A booking for a cancelled event cannot be cancelled."
            )

        if event.status is EventStatus.COMPLETED:
            raise ConflictError(
                "A booking for a completed event cannot be cancelled."
            )

        available_after_restoration = (
            event.tickets_available + booking.quantity
        )
        if not 0 <= available_after_restoration <= event.total_tickets:
            raise ConflictError(
                "Cancelling this booking would make ticket inventory invalid."
            )

        event.tickets_available = available_after_restoration
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)

        await session.flush([booking])
        await booking_repository.refresh_booking(session, booking)

        audit_service.record_action(
            session,
            actor_id=current_user.id,
            action=AuditAction.BOOKING_CANCELLED,
            entity_type=AuditEntityType.BOOKING,
            entity_id=booking.id,
        )

        response = _booking_response(
            booking,
            event,
            review=booking.review,
        )

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


def _get_constraint_name(error: IntegrityError) -> str | None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    diagnostics = getattr(original_error, "diag", None)

    return (
        getattr(original_error, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(diagnostics, "constraint_name", None)
    )


def _booking_response(
    booking: Booking,
    event: Event,
    *,
    review: Review | None = None,
) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        event_id=booking.event_id,
        event_title=event.title,
        event_venue=event.venue,
        event_datetime=event.event_datetime,
        event_organizer_name=event.organizer.name,
        event_status=event.status,
        review=review,
        quantity=booking.quantity,
        status=booking.status,
        booked_at=booking.booked_at,
        cancelled_at=booking.cancelled_at,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )
