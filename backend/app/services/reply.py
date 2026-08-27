from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReplyRole
from app.models.user import User
from app.repositories import reply as reply_repository
from app.schemas.reply import ReplyCreate, ReplyResponse
from app.services.auth import AccountUnavailableError


class ReplyReviewNotFoundError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("The selected Review does not exist.")


class ReplyCreationForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("You do not have permission to reply to this Review.")


class OrganizerReplyOwnershipError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("You can only reply to Reviews for your own Events.")


class OrganizerReplyAlreadyExistsError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("An Organizer Reply already exists for this Review.")


class AdminReplyAlreadyExistsError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("An Admin Reply already exists for this Review.")


class UserAlreadyRepliedError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("You have already replied to this Review.")


class InvalidReplyBodyError(Exception):
    def __init__(self) -> None:
        super().__init__("The Reply body cannot be empty.")


class ReplyTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The Reply could not be saved.")


async def create_reply(
    session: AsyncSession,
    current_user: User,
    review_id: UUID,
    request: ReplyCreate,
    *,
    can_reply_own_event: bool,
    can_reply_any: bool,
) -> ReplyResponse:
    replier_role: ReplyRole | None = None

    try:
        _ensure_account_is_available(current_user)
        _ensure_reply_body_is_valid(request)

        review = await reply_repository.get_review_for_reply(
            session,
            review_id,
        )
        if review is None:
            raise ReplyReviewNotFoundError(review_id)

        if can_reply_any:
            replier_role = ReplyRole.ADMIN
        elif can_reply_own_event:
            if review.booking.event.organizer_id != current_user.id:
                raise OrganizerReplyOwnershipError(review_id)
            replier_role = ReplyRole.ORGANIZER
        else:
            raise ReplyCreationForbiddenError()

        existing_role_reply = (
            await reply_repository.get_reply_by_review_and_role(
                session,
                review_id=review_id,
                replier_role=replier_role,
            )
        )
        if existing_role_reply is not None:
            _raise_role_position_occupied(review_id, replier_role)

        existing_user_reply = (
            await reply_repository.get_reply_by_review_and_user(
                session,
                review_id=review_id,
                user_id=current_user.id,
            )
        )
        if existing_user_reply is not None:
            raise UserAlreadyRepliedError(review_id)

        reply = reply_repository.add_reply(
            session,
            review_id=review_id,
            user_id=current_user.id,
            replier_role=replier_role,
            body=request.body,
        )
        await reply_repository.flush_reply(session, reply)

        response = ReplyResponse.model_validate(reply)

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        constraint_name = _get_constraint_name(error)
        if constraint_name == "uq_replies_review_id_replier_role":
            if replier_role is None:
                raise ReplyTransactionError() from error
            _raise_role_position_occupied(review_id, replier_role, cause=error)
        if constraint_name == "uq_replies_review_id_user_id":
            raise UserAlreadyRepliedError(review_id) from error
        raise ReplyTransactionError() from error
    except SQLAlchemyError as error:
        await session.rollback()
        raise ReplyTransactionError() from error
    except Exception:
        await session.rollback()
        raise


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise AccountUnavailableError


def _ensure_reply_body_is_valid(request: ReplyCreate) -> None:
    if not request.body.strip():
        raise InvalidReplyBodyError()


def _raise_role_position_occupied(
    review_id: UUID,
    replier_role: ReplyRole,
    *,
    cause: Exception | None = None,
) -> NoReturn:
    if replier_role is ReplyRole.ADMIN:
        error = AdminReplyAlreadyExistsError(review_id)
    else:
        error = OrganizerReplyAlreadyExistsError(review_id)

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
