from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.dependencies import (
    DatabaseSession,
    PermissionGrant,
    require_any_permission,
    require_permission,
)
from app.core.permissions import (
    CANCEL_ANY_BOOKING,
    CANCEL_OWN_BOOKING,
    CREATE_BOOKINGS,
)
from app.models.enums import NotificationType
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking import cancel_booking, create_booking
from app.tasks.notification import create_notification_in_background


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_booking",
)
async def create_booking_endpoint(
    request: BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[
        User,
        Depends(require_permission(CREATE_BOOKINGS)),
    ],
    session: DatabaseSession,
) -> BookingResponse:
    booking = await create_booking(session, current_user, request)
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.BOOKING_CONFIRMED,
        related_booking_id=booking.id,
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
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                CANCEL_OWN_BOOKING,
                CANCEL_ANY_BOOKING,
            )
        ),
    ],
    session: DatabaseSession,
) -> BookingResponse:
    booking = await cancel_booking(
        session,
        permission_grant.user,
        booking_id,
        can_cancel_own=permission_grant.allows(CANCEL_OWN_BOOKING),
        can_cancel_any=permission_grant.allows(CANCEL_ANY_BOOKING),
    )
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.BOOKING_CANCELLED,
        related_booking_id=booking.id,
    )
    return booking
