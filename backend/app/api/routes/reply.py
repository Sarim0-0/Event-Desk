from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.dependencies import (
    DatabaseSession,
    PermissionGrant,
    require_any_permission,
)
from app.core.permissions import (
    REPLY_TO_ANY_REVIEW,
    REPLY_TO_OWN_EVENT_REVIEWS,
)
from app.models.enums import NotificationType
from app.schemas.reply import ReplyCreate, ReplyResponse
from app.services.reply import create_reply
from app.tasks.notification import create_notification_in_background


router = APIRouter(prefix="/reviews", tags=["Replies"])


@router.post(
    "/{review_id}/replies",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
    name="create_reply",
)
async def create_reply_endpoint(
    review_id: UUID,
    request: ReplyCreate,
    background_tasks: BackgroundTasks,
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
    reply = await create_reply(
        session,
        permission_grant.user,
        review_id,
        request,
        can_reply_own_event=permission_grant.allows(
            REPLY_TO_OWN_EVENT_REVIEWS
        ),
        can_reply_any=permission_grant.allows(REPLY_TO_ANY_REVIEW),
    )
    background_tasks.add_task(
        create_notification_in_background,
        notification_type=NotificationType.REVIEW_REPLIED,
        related_review_id=reply.review_id,
    )
    return reply
