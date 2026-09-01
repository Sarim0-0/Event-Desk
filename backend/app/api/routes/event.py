from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    require_own_or_any_permission,
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
from app.schemas.event import (
    CategoryResponse,
    EventCreateRequest,
    EventListQuery,
    EventResponse,
    EventUpdate,
    PaginatedEventsResponse,
    TagResponse,
)
from app.services.event import (
    cancel_event,
    create_event,
    list_categories,
    list_completed_events,
    list_draft_events,
    list_events,
    list_tags,
    update_event,
)
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
    current_user: CurrentUser,
    session: DatabaseSession,
) -> PaginatedEventsResponse:
    return await list_events(session, current_user, query)


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    name="list_event_categories",
)
async def list_categories_endpoint(
    _current_user: CurrentUser,
    session: DatabaseSession,
) -> list[CategoryResponse]:
    return await list_categories(session)


@router.get(
    "/tags",
    response_model=list[TagResponse],
    status_code=status.HTTP_200_OK,
    name="list_event_tags",
)
async def list_tags_endpoint(
    _current_user: CurrentUser,
    session: DatabaseSession,
) -> list[TagResponse]:
    return await list_tags(session)


@router.get(
    "/completed",
    response_model=PaginatedEventsResponse,
    status_code=status.HTTP_200_OK,
    name="list_completed_events",
)
async def list_completed_events_endpoint(
    query: Annotated[EventListQuery, Query()],
    current_user: CurrentUser,
    session: DatabaseSession,
) -> PaginatedEventsResponse:
    return await list_completed_events(session, current_user, query)


@router.get(
    "/drafts",
    response_model=PaginatedEventsResponse,
    status_code=status.HTTP_200_OK,
    name="list_draft_events",
)
async def list_draft_events_endpoint(
    query: Annotated[EventListQuery, Query()],
    current_user: CurrentUser,
    can_view_any: Annotated[
        bool,
        Depends(
            require_own_or_any_permission(
                EDIT_OWN_EVENT,
                EDIT_ANY_EVENT,
            )
        ),
    ],
    session: DatabaseSession,
) -> PaginatedEventsResponse:
    return await list_draft_events(
        session,
        current_user,
        query,
        can_view_any=can_view_any,
    )


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
    current_user: CurrentUser,
    can_edit_any: Annotated[
        bool,
        Depends(
            require_own_or_any_permission(
                EDIT_OWN_EVENT,
                EDIT_ANY_EVENT,
            )
        ),
    ],
    session: DatabaseSession,
) -> EventResponse:
    event = await update_event(
        session,
        current_user,
        event_id,
        request,
        can_edit_any=can_edit_any,
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
    current_user: CurrentUser,
    can_cancel_any: Annotated[
        bool,
        Depends(
            require_own_or_any_permission(
                CANCEL_OWN_EVENT,
                CANCEL_ANY_EVENT,
            )
        ),
    ],
    session: DatabaseSession,
) -> EventResponse:
    event = await cancel_event(
        session,
        current_user,
        event_id,
        can_cancel_any=can_cancel_any,
    )
    background_tasks.add_task(
        create_event_cancellation_notifications_in_background,
        event_id=event.id,
    )
    return event
