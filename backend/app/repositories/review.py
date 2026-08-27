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


async def flush_review(
    session: AsyncSession,
    review: Review,
) -> None:
    await session.flush([review])
