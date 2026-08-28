from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

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
    VIEW_PUBLISHED_EVENTS,
)
from app.models.user import User
from app.schemas.event import (
    EventCreateRequest,
    EventListQuery,
    EventResponse,
    EventUpdate,
    PaginatedEventsResponse,
)
from app.services.event import cancel_event, create_event, list_events, update_event
from app.tasks.event_availability import (
    broadcast_event_availability_in_background,
)
from app.tasks.notification import (
    create_event_cancellation_notifications_in_background,
)


router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=PaginatedEventsResponse,
    status_code=status.HTTP_200_OK,
    name="list_events",
)
async def list_events_endpoint(
    query: Annotated[EventListQuery, Query()],
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_PUBLISHED_EVENTS)),
    ],
    session: DatabaseSession,
) -> PaginatedEventsResponse:
    return await list_events(session, query)


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
    background_tasks: BackgroundTasks,
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
    event = await update_event(
        session,
        permission_grant.user,
        event_id,
        request,
        can_edit_own=permission_grant.allows(EDIT_OWN_EVENT),
        can_edit_any=permission_grant.allows(EDIT_ANY_EVENT),
    )
    if "total_tickets" in request.model_fields_set:
        background_tasks.add_task(
            broadcast_event_availability_in_background,
            event_id=event.id,
        )
    return event


@router.post(
    "/{event_id}/cancel",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    name="cancel_event",
)
async def cancel_event_endpoint(
    event_id: UUID,
    background_tasks: BackgroundTasks,
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
    event = await cancel_event(
        session,
        permission_grant.user,
        event_id,
        can_cancel_own=permission_grant.allows(CANCEL_OWN_EVENT),
        can_cancel_any=permission_grant.allows(CANCEL_ANY_EVENT),
    )
    background_tasks.add_task(
        create_event_cancellation_notifications_in_background,
        event_id=event.id,
    )
    return event
