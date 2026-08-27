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
    CREATE_REVIEWS,
    DELETE_ANY_REVIEW,
    DELETE_OWN_REVIEW,
    EDIT_ANY_REVIEW,
    EDIT_OWN_REVIEW,
)
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.review import create_review, delete_review, update_review


router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_review",
)
async def create_review_endpoint(
    request: ReviewCreate,
    current_user: Annotated[
        User,
        Depends(require_permission(CREATE_REVIEWS)),
    ],
    session: DatabaseSession,
) -> ReviewResponse:
    return await create_review(session, current_user, request)


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
