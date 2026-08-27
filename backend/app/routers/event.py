from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CREATE_EVENTS,
    EDIT_ANY_EVENT,
    EDIT_OWN_EVENT,
)
from app.database.dependencies import get_db_session
from app.dependencies.auth import (
    PermissionGrant,
    require_any_permission,
    require_permission,
)
from app.models.user import User
from app.schemas.event import EventCreateRequest, EventResponse, EventUpdate
from app.services.auth import AccountUnavailableError
from app.services.event import (
    CategoryNotFoundError,
    EmptyEventUpdateError,
    EventCapacityBelowSoldTicketsError,
    EventNotEditableError,
    EventNotFoundError,
    EventUpdateForbiddenError,
    EventUpdateTransactionError,
    InvalidEventUpdateError,
    TagsNotFoundError,
    create_event,
    update_event,
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
    current_user: Annotated[
        User,
        Depends(require_permission(CREATE_EVENTS)),
    ],
    session: DatabaseSession,
) -> EventResponse:
    try:
        return await create_event(session, current_user, request)
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


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    name="update_event",
)
async def update_event_endpoint(
    event_id: UUID,
    request: EventUpdate,
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                EDIT_OWN_EVENT,
                EDIT_ANY_EVENT,
            )
        ),
    ],
    session: DatabaseSession,
) -> EventResponse:
    try:
        return await update_event(
            session,
            permission_grant.user,
            event_id,
            request,
            can_edit_own=permission_grant.allows(EDIT_OWN_EVENT),
            can_edit_any=permission_grant.allows(EDIT_ANY_EVENT),
        )
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except EventUpdateForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except EventNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except EventNotEditableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except (EmptyEventUpdateError, InvalidEventUpdateError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except (CategoryNotFoundError, TagsNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except EventCapacityBelowSoldTicketsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except EventUpdateTransactionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The Event could not be updated.",
        ) from error
