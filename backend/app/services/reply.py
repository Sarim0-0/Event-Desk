from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import ReplyRole
from app.models.user import User
from app.repositories import reply as reply_repository
from app.schemas.reply import ReplyCreate, ReplyResponse


async def create_reply(
    session: AsyncSession,
    current_user: User,
    review_id: UUID,
    request: ReplyCreate,
    *,
    can_reply_any: bool,
) -> ReplyResponse:
    replier_role: ReplyRole | None = None

    try:
        review = await reply_repository.get_review_for_reply(
            session,
            review_id,
        )
        if review is None:
            raise NotFoundError("The selected Review does not exist.")

        if can_reply_any:
            replier_role = ReplyRole.ADMIN
        else:
            if review.booking.event.organizer_id != current_user.id:
                raise ForbiddenError(
                    "You can only reply to Reviews for your own Events."
                )
            replier_role = ReplyRole.ORGANIZER

        existing_role_reply = (
            await reply_repository.get_reply_by_review_and_role(
                session,
                review_id=review_id,
                replier_role=replier_role,
            )
        )
        if existing_role_reply is not None:
            _raise_role_position_occupied(replier_role)

        existing_user_reply = (
            await reply_repository.get_reply_by_review_and_user(
                session,
                review_id=review_id,
                user_id=current_user.id,
            )
        )
        if existing_user_reply is not None:
            raise ConflictError(
                "You have already replied to this Review."
            )

        reply = reply_repository.add_reply(
            session,
            review_id=review_id,
            user_id=current_user.id,
            replier_role=replier_role,
            body=request.body,
        )
        await session.flush([reply])

        response = ReplyResponse.model_validate(reply)

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        constraint_name = _get_constraint_name(error)
        if constraint_name == "uq_replies_review_id_replier_role":
            if replier_role is None:
                raise
            _raise_role_position_occupied(replier_role, cause=error)
        if constraint_name == "uq_replies_review_id_user_id":
            raise ConflictError(
                "You have already replied to this Review."
            ) from error
        raise
    except Exception:
        await session.rollback()
        raise


def _raise_role_position_occupied(
    replier_role: ReplyRole,
    *,
    cause: Exception | None = None,
) -> NoReturn:
    if replier_role is ReplyRole.ADMIN:
        error = ConflictError(
            "An Admin Reply already exists for this Review."
        )
    else:
        error = ConflictError(
            "An Organizer Reply already exists for this Review."
        )

    if cause is not None:
        raise error from cause
    raise error


def _get_constraint_name(error: IntegrityError) -> str | None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    diagnostics = getattr(original_error, "diag", None)

    return (
        getattr(original_error, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(diagnostics, "constraint_name", None)
    )
