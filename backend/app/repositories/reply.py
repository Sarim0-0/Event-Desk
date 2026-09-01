from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.booking import Booking
from app.models.enums import ReplyRole
from app.models.review import Reply, Review


async def get_review_for_reply(
    session: AsyncSession,
    review_id: UUID,
) -> Review | None:
    statement = (
        select(Review)
        .options(
            joinedload(Review.booking).joinedload(Booking.event),
        )
        .where(Review.id == review_id)
    )
    return await session.scalar(statement)


async def get_reply_by_review_and_role(
    session: AsyncSession,
    *,
    review_id: UUID,
    replier_role: ReplyRole,
) -> Reply | None:
    statement = select(Reply).where(
        Reply.review_id == review_id,
        Reply.replier_role == replier_role,
    )
    return await session.scalar(statement)


async def get_reply_by_review_and_user(
    session: AsyncSession,
    *,
    review_id: UUID,
    user_id: UUID,
) -> Reply | None:
    statement = select(Reply).where(
        Reply.review_id == review_id,
        Reply.user_id == user_id,
    )
    return await session.scalar(statement)


def add_reply(
    session: AsyncSession,
    *,
    review_id: UUID,
    user_id: UUID,
    replier_role: ReplyRole,
    body: str,
) -> Reply:
    reply = Reply(
        review_id=review_id,
        user_id=user_id,
        replier_role=replier_role,
        body=body,
    )
    session.add(reply)
    return reply
