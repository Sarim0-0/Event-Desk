from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.dependencies.auth import CurrentUser
from app.schemas.event import EventCreateRequest, EventResponse
from app.services.auth import AccountUnavailableError
from app.services.event import (
    CategoryNotFoundError,
    EventCreationForbiddenError,
    TagsNotFoundError,
    create_event,
)


router = APIRouter(prefix="/events", tags=["Events"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_endpoint(
    request: EventCreateRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EventResponse:
    try:
        return await create_event(session, current_user, request)
    except EventCreationForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create events.",
        ) from error
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except TagsNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
