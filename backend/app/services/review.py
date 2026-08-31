from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import BookingStatus
from app.models.user import User
from app.repositories import review as review_repository
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate


async def create_review(
    session: AsyncSession,
    current_user: User,
    request: ReviewCreate,
) -> ReviewResponse:
    try:
        booking = await review_repository.get_booking_for_review(
            session,
            request.booking_id,
        )
        if booking is None:
            raise NotFoundError("The selected booking does not exist.")

        if booking.user_id != current_user.id:
            raise ForbiddenError(
                "You can only review an event using your own booking."
            )

        if booking.status is not BookingStatus.CONFIRMED:
            raise ConflictError("Only a confirmed booking can be reviewed.")

        event = booking.event
        if event is None or event.deleted_at is not None:
            raise NotFoundError(
                "The event for this booking does not exist."
            )

        existing_review = await review_repository.get_review_by_booking_id(
            session,
            booking.id,
        )
        if existing_review is not None:
            raise ConflictError(
                "A review already exists for this booking."
            )

        review = review_repository.add_review(
            session,
            booking_id=booking.id,
            rating=request.rating,
            comment=request.comment,
        )
        await session.flush([review])

        response = ReviewResponse.model_validate(review)

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        if _get_constraint_name(error) == "uq_reviews_booking_id":
            raise ConflictError(
                "A review already exists for this booking."
            ) from error
        raise
    except Exception:
        await session.rollback()
        raise


async def update_review(
    session: AsyncSession,
    current_user: User,
    review_id: UUID,
    request: ReviewUpdate,
    *,
    can_update_own: bool,
    can_update_any: bool,
) -> ReviewResponse:
    try:
        changes = request.model_dump(exclude_unset=True)

        review = await review_repository.get_review_by_id(session, review_id)
        if review is None:
            raise NotFoundError("The selected review does not exist.")

        if not can_update_any and (
            not can_update_own
            or review.booking.user_id != current_user.id
        ):
            raise ForbiddenError(
                "You do not have permission to edit this review."
            )

        review_repository.update_review(
            review,
            rating=changes.get("rating"),
            comment=changes.get("comment"),
        )
        await session.flush([review])
        await review_repository.refresh_review(session, review)

        response = ReviewResponse.model_validate(review)

        await session.commit()
        return response
    except Exception:
        await session.rollback()
        raise


async def delete_review(
    session: AsyncSession,
    current_user: User,
    review_id: UUID,
    *,
    can_delete_own: bool,
    can_delete_any: bool,
) -> None:
    try:
        review = await review_repository.get_review_by_id(session, review_id)
        if review is None:
            raise NotFoundError("The selected review does not exist.")

        if not can_delete_any and (
            not can_delete_own
            or review.booking.user_id != current_user.id
        ):
            raise ForbiddenError(
                "You do not have permission to delete this review."
            )

        await review_repository.delete_review(session, review)
        await session.flush([review])

        await session.commit()
    except Exception:
        await session.rollback()
        raise


def _get_constraint_name(error: IntegrityError) -> str | None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    diagnostics = getattr(original_error, "diag", None)

    return (
        getattr(original_error, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(diagnostics, "constraint_name", None)
    )
