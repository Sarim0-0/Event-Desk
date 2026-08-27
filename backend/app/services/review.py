from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CREATE_REVIEWS
from app.models.enums import BookingStatus
from app.models.user import User
from app.repositories import rbac as rbac_repository
from app.repositories import review as review_repository
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.auth import AccountUnavailableError


class ReviewCreationForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("You do not have permission to leave a review.")


class ReviewBookingNotFoundError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("The selected booking does not exist.")


class ReviewBookingOwnershipError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("You can only review an event using your own booking.")


class ReviewBookingNotEligibleError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("Only a confirmed booking can be reviewed.")


class ReviewEventNotFoundError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("The event for this booking does not exist.")


class ReviewAlreadyExistsError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("A review already exists for this booking.")


class InvalidReviewInputError(Exception):
    def __init__(self) -> None:
        super().__init__("The review information is invalid.")


class ReviewTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The review could not be saved.")


async def create_review(
    session: AsyncSession,
    current_user: User,
    request: ReviewCreate,
) -> ReviewResponse:
    try:
        _ensure_account_is_available(current_user)
        _ensure_review_input_is_valid(request)

        can_create_review = await rbac_repository.role_has_permission(
            session,
            current_user.role_id,
            CREATE_REVIEWS,
        )
        if not can_create_review:
            raise ReviewCreationForbiddenError()

        booking = await review_repository.get_booking_for_review(
            session,
            request.booking_id,
        )
        if booking is None:
            raise ReviewBookingNotFoundError(request.booking_id)

        if booking.user_id != current_user.id:
            raise ReviewBookingOwnershipError(booking.id)

        if booking.status is not BookingStatus.CONFIRMED:
            raise ReviewBookingNotEligibleError(booking.id)

        event = booking.event
        if event is None or event.deleted_at is not None:
            raise ReviewEventNotFoundError(booking.event_id)

        existing_review = await review_repository.get_review_by_booking_id(
            session,
            booking.id,
        )
        if existing_review is not None:
            raise ReviewAlreadyExistsError(booking.id)

        review = review_repository.add_review(
            session,
            booking_id=booking.id,
            rating=request.rating,
            comment=request.comment,
        )
        await review_repository.flush_review(session, review)

        response = ReviewResponse.model_validate(review)

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        if _get_constraint_name(error) == "uq_reviews_booking_id":
            raise ReviewAlreadyExistsError(request.booking_id) from error
        raise ReviewTransactionError() from error
    except SQLAlchemyError as error:
        await session.rollback()
        raise ReviewTransactionError() from error
    except Exception:
        await session.rollback()
        raise


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise AccountUnavailableError


def _ensure_review_input_is_valid(request: ReviewCreate) -> None:
    if not 1 <= request.rating <= 5 or not request.comment.strip():
        raise InvalidReviewInputError()


def _get_constraint_name(error: IntegrityError) -> str | None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    diagnostics = getattr(original_error, "diag", None)

    return (
        getattr(original_error, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(diagnostics, "constraint_name", None)
    )
