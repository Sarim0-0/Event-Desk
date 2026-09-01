from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.booking import Booking
from app.models.event import Event
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


async def list_manageable_reviews(
    session: AsyncSession,
    *,
    organizer_id: UUID | None,
) -> list[Review]:
    """Load Reviews with the context required by the management view."""

    statement = (
        select(Review)
        .join(Review.booking)
        .join(Booking.event)
        .options(
            joinedload(Review.booking)
            .joinedload(Booking.event)
            .joinedload(Event.organizer),
            joinedload(Review.booking).joinedload(Booking.user),
            selectinload(Review.replies),
        )
        .order_by(
            Event.event_datetime.desc(),
            Event.title.asc(),
            Review.created_at.desc(),
            Review.id.desc(),
        )
    )
    if organizer_id is not None:
        statement = statement.where(Event.organizer_id == organizer_id)

    reviews = await session.scalars(statement)
    return list(reviews.unique().all())


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
