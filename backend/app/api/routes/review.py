from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    PermissionGrant,
    require_any_permission,
)
from app.core.permissions import (
    DELETE_ANY_REVIEW,
    DELETE_OWN_REVIEW,
    EDIT_ANY_REVIEW,
    EDIT_OWN_REVIEW,
    REPLY_TO_ANY_REVIEW,
    REPLY_TO_OWN_EVENT_REVIEWS,
)
from app.models.enums import NotificationType
from app.schemas.review import (
    EventReviewsResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)
from app.services.review import (
    create_review,
    delete_review,
    list_event_reviews,
    update_review,
)
from app.tasks.notification import create_notification_in_background


router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get(
    "",
    response_model=list[EventReviewsResponse],
    status_code=status.HTTP_200_OK,
    name="list_event_reviews",
)
async def list_event_reviews_endpoint(
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                REPLY_TO_OWN_EVENT_REVIEWS,
                REPLY_TO_ANY_REVIEW,
            )
        ),
    ],
    session: DatabaseSession,
) -> list[EventReviewsResponse]:
    return await list_event_reviews(
        session,
        permission_grant.user,
        can_view_own_events=permission_grant.allows(
            REPLY_TO_OWN_EVENT_REVIEWS
        ),
        can_view_any_event=permission_grant.allows(REPLY_TO_ANY_REVIEW),
    )


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_review",
)
async def create_review_endpoint(
    request: ReviewCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> ReviewResponse:
    review = await create_review(session, current_user, request)
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.EVENT_REVIEWED,
        related_review_id=review.id,
    )
    return review


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    name="update_review",
)
async def update_review_endpoint(
    review_id: UUID,
    request: ReviewUpdate,
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                EDIT_OWN_REVIEW,
                EDIT_ANY_REVIEW,
            )
        ),
    ],
    session: DatabaseSession,
) -> ReviewResponse:
    return await update_review(
        session,
        permission_grant.user,
        review_id,
        request,
        can_update_own=permission_grant.allows(EDIT_OWN_REVIEW),
        can_update_any=permission_grant.allows(EDIT_ANY_REVIEW),
    )


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    name="delete_review",
)
async def delete_review_endpoint(
    review_id: UUID,
    permission_grant: Annotated[
        PermissionGrant,
        Depends(
            require_any_permission(
                DELETE_OWN_REVIEW,
                DELETE_ANY_REVIEW,
            )
        ),
    ],
    session: DatabaseSession,
) -> None:
    await delete_review(
        session,
        permission_grant.user,
        review_id,
        can_delete_own=permission_grant.allows(DELETE_OWN_REVIEW),
        can_delete_any=permission_grant.allows(DELETE_ANY_REVIEW),
    )
