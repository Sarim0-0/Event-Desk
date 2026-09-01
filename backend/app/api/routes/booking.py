from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    require_own_or_any_permission,
)
from app.core.permissions import (
    CANCEL_ANY_BOOKING,
    CANCEL_OWN_BOOKING,
)
from app.models.enums import NotificationType, UserRole
from app.schemas.booking import (
    BookingCreate,
    BookingListQuery,
    BookingResponse,
    PaginatedBookingsResponse,
)
from app.services.booking import (
    cancel_booking,
    create_booking,
    list_own_bookings,
)
from app.tasks.event_availability import (
    broadcast_event_availability_in_background,
)
from app.tasks.notification import create_notification_in_background


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get(
    "",
    response_model=PaginatedBookingsResponse,
    status_code=status.HTTP_200_OK,
    name="list_own_bookings",
)
async def list_own_bookings_endpoint(
    query: Annotated[BookingListQuery, Query()],
    current_user: CurrentUser,
    session: DatabaseSession,
) -> PaginatedBookingsResponse:
    return await list_own_bookings(session, current_user, query)


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_booking",
)
async def create_booking_endpoint(
    request: BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> BookingResponse:
    booking = await create_booking(session, current_user, request)
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.BOOKING_CONFIRMED,
        related_booking_id=booking.id,
    )
    background_tasks.add_task(
        broadcast_event_availability_in_background,
        event_id=booking.event_id,
    )
    return booking


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    name="cancel_booking",
)
async def cancel_booking_endpoint(
    booking_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    can_cancel_any: Annotated[
        bool,
        Depends(
            require_own_or_any_permission(
                CANCEL_OWN_BOOKING,
                CANCEL_ANY_BOOKING,
            )
        ),
    ],
    session: DatabaseSession,
) -> BookingResponse:
    booking = await cancel_booking(
        session,
        current_user,
        booking_id,
        can_cancel_any=can_cancel_any,
    )
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.BOOKING_CANCELLED,
        related_booking_id=booking.id,
        cancelled_by_admin=(
            current_user.role.name == UserRole.ADMIN.value
            and booking.user_id != current_user.id
        ),
    )
    background_tasks.add_task(
        broadcast_event_availability_in_background,
        event_id=booking.event_id,
    )
    return booking
