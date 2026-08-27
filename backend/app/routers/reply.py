from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    REPLY_TO_ANY_REVIEW,
    REPLY_TO_OWN_EVENT_REVIEWS,
)
from app.database.dependencies import get_db_session
from app.dependencies.auth import PermissionGrant, require_any_permission
from app.schemas.reply import ReplyCreate, ReplyResponse
from app.services.auth import AccountUnavailableError
from app.services.reply import (
    AdminReplyAlreadyExistsError,
    InvalidReplyBodyError,
    OrganizerReplyAlreadyExistsError,
    OrganizerReplyOwnershipError,
    ReplyCreationForbiddenError,
    ReplyReviewNotFoundError,
    ReplyTransactionError,
    UserAlreadyRepliedError,
    create_reply,
)


router = APIRouter(prefix="/reviews", tags=["Replies"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/{review_id}/replies",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_reply",
)
async def create_reply_endpoint(
    review_id: UUID,
    request: ReplyCreate,
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
) -> ReplyResponse:
    try:
        return await create_reply(
            session,
            permission_grant.user,
            review_id,
            request,
            can_reply_own_event=permission_grant.allows(
                REPLY_TO_OWN_EVENT_REVIEWS
            ),
            can_reply_any=permission_grant.allows(REPLY_TO_ANY_REVIEW),
        )
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error
    except (ReplyCreationForbiddenError, OrganizerReplyOwnershipError) as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ReplyReviewNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        OrganizerReplyAlreadyExistsError,
        AdminReplyAlreadyExistsError,
        UserAlreadyRepliedError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidReplyBodyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except ReplyTransactionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The Reply could not be saved.",
        ) from error
