from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CREATE_REVIEWS
from app.database.dependencies import get_db_session
from app.dependencies.auth import require_permission
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.auth import AccountUnavailableError
from app.services.review import (
    InvalidReviewInputError,
    ReviewAlreadyExistsError,
    ReviewBookingNotEligibleError,
    ReviewBookingNotFoundError,
    ReviewBookingOwnershipError,
    ReviewEventNotFoundError,
    ReviewTransactionError,
    create_review,
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
