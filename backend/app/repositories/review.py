from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.booking import Booking
from app.models.review import Review


async def get_booking_for_review(
    session: AsyncSession,
    booking_id: UUID,
) -> Booking | None:
    statement = (
        select(Booking)
        .options(joinedload(Booking.event))
        .where(Booking.id == booking_id)
    )
    return await session.scalar(statement)


async def get_review_by_booking_id(
    session: AsyncSession,
    booking_id: UUID,
) -> Review | None:
    statement = select(Review).where(Review.booking_id == booking_id)
    return await session.scalar(statement)


async def get_review_by_id(
    session: AsyncSession,
    review_id: UUID,
) -> Review | None:
    statement = (
        select(Review)
        .options(joinedload(Review.booking))
        .where(Review.id == review_id)
    )
    return await session.scalar(statement)


def add_review(
    session: AsyncSession,
    *,
    booking_id: UUID,
    rating: int,
    comment: str,
) -> Review:
    review = Review(
        booking_id=booking_id,
        rating=rating,
        comment=comment,
    )
    session.add(review)
    return review


def update_review(
    review: Review,
    *,
    rating: int | None = None,
    comment: str | None = None,
) -> Review:
    if rating is not None:
        review.rating = rating
    if comment is not None:
        review.comment = comment
    return review


async def delete_review(
    session: AsyncSession,
    review: Review,
) -> None:
    await session.delete(review)


async def refresh_review(
    session: AsyncSession,
    review: Review,
) -> Review:
    await session.refresh(
        review,
        attribute_names=["id", "created_at", "updated_at"],
    )
    return review
