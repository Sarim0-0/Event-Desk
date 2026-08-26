from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.dependencies.auth import CurrentUser
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.auth import AccountUnavailableError
from app.services.booking import (
    BookingCreationForbiddenError,
    BookingEventNotFoundError,
    EventNotBookableError,
    InsufficientTicketsError,
    InvalidBookingQuantityError,
    create_booking,
)


router = APIRouter(prefix="/bookings", tags=["Bookings"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_booking",
)
async def create_booking_endpoint(
    request: BookingCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> BookingResponse:
    try:
        return await create_booking(session, current_user, request)
    except BookingCreationForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to book tickets.",
        ) from error
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except BookingEventNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except EventNotBookableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidBookingQuantityError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantity must be at least 1.",
        ) from error
    except InsufficientTicketsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
