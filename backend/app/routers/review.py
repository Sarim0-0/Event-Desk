from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CREATE_REVIEWS,
    DELETE_ANY_REVIEW,
    DELETE_OWN_REVIEW,
    EDIT_ANY_REVIEW,
    EDIT_OWN_REVIEW,
)
from app.database.dependencies import get_db_session
from app.dependencies.auth import (
    PermissionGrant,
    require_any_permission,
    require_permission,
)
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.auth import AccountUnavailableError
from app.services.review import (
    EmptyReviewUpdateError,
    InvalidReviewUpdateError,
    InvalidReviewInputError,
    ReviewAlreadyExistsError,
    ReviewBookingNotEligibleError,
    ReviewBookingNotFoundError,
    ReviewBookingOwnershipError,
    ReviewDeletionForbiddenError,
    ReviewDeletionTransactionError,
    ReviewEventNotFoundError,
    ReviewNotFoundError,
    ReviewTransactionError,
    ReviewUpdateForbiddenError,
    ReviewUpdateTransactionError,
    create_review,
    delete_review,
    update_review,
)


router = APIRouter(prefix="/reviews", tags=["Reviews"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


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
    try:
        return await create_review(session, current_user, request)
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except ReviewBookingOwnershipError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ReviewBookingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ReviewEventNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ReviewBookingNotEligibleError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ReviewAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidReviewInputError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except ReviewTransactionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The review could not be saved.",
        ) from error


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
    try:
        return await update_review(
            session,
            permission_grant.user,
            review_id,
            request,
            can_update_own=permission_grant.allows(EDIT_OWN_REVIEW),
            can_update_any=permission_grant.allows(EDIT_ANY_REVIEW),
        )
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except ReviewUpdateForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ReviewNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (EmptyReviewUpdateError, InvalidReviewUpdateError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except ReviewUpdateTransactionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The review could not be updated.",
        ) from error


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
    try:
        await delete_review(
            session,
            permission_grant.user,
            review_id,
            can_delete_own=permission_grant.allows(DELETE_OWN_REVIEW),
            can_delete_any=permission_grant.allows(DELETE_ANY_REVIEW),
        )
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except ReviewDeletionForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ReviewNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ReviewDeletionTransactionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The review could not be deleted.",
        ) from error
