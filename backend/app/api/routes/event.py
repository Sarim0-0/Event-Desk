from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    DatabaseSession,
    PermissionGrant,
    require_any_permission,
    require_permission,
)
from app.core.permissions import (
    CANCEL_ANY_EVENT,
    CANCEL_OWN_EVENT,
    CREATE_EVENTS,
    EDIT_ANY_EVENT,
    EDIT_OWN_EVENT,
)
from app.models.user import User
from app.schemas.event import EventCreateRequest, EventResponse, EventUpdate
from app.services.event import cancel_event, create_event, update_event


router = APIRouter(prefix="/events", tags=["Events"])


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
    return await create_event(session, current_user, request)


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
    return await update_event(
        session,
        permission_grant.user,
        event_id,
        request,
        can_edit_own=permission_grant.allows(EDIT_OWN_EVENT),
        can_edit_any=permission_grant.allows(EDIT_ANY_EVENT),
    )


@router.post(
    "/{event_id}/cancel",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    name="cancel_event",
)
async def cancel_event_endpoint(
    event_id: UUID,
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                CANCEL_OWN_EVENT,
                CANCEL_ANY_EVENT,
            )
        ),
    ],
    session: DatabaseSession,
) -> EventResponse:
    return await cancel_event(
        session,
        permission_grant.user,
        event_id,
        can_cancel_own=permission_grant.allows(CANCEL_OWN_EVENT),
        can_cancel_any=permission_grant.allows(CANCEL_ANY_EVENT),
    )
