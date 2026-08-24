from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.events.models import Event
    from app.modules.notifications.models import Notification
    from app.modules.users.models import User


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_between_one_and_five"),
        UniqueConstraint("user_id", "event_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="reviews")
    event: Mapped[Event] = relationship(back_populates="reviews")
    replies: Mapped[list[Reply]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="related_review",
        foreign_keys="Notification.related_review_id",
    )


class Reply(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "replies"

    review_id: Mapped[UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    review: Mapped[Review] = relationship(back_populates="replies")
    user: Mapped[User] = relationship(back_populates="replies")
