from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ReplyRole

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.notification import Notification
    from app.models.user import User


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_reviews"),
        CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="ck_reviews_rating_between_one_and_five",
        ),
        UniqueConstraint(
            "booking_id",
            name="uq_reviews_booking_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "bookings.id",
            name="fk_reviews_booking_id_bookings",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    booking: Mapped[Booking] = relationship(back_populates="review")
    replies: Mapped[list[Reply]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="related_review",
        foreign_keys="Notification.related_review_id",
    )


class Reply(Base):
    __tablename__ = "replies"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_replies"),
        UniqueConstraint(
            "review_id",
            "replier_role",
            name="uq_replies_review_id_replier_role",
        ),
        UniqueConstraint(
            "review_id",
            "user_id",
            name="uq_replies_review_id_user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    review_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "reviews.id",
            name="fk_replies_review_id_reviews",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_replies_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    replier_role: Mapped[ReplyRole] = mapped_column(
        SqlEnum(
            ReplyRole,
            name="ck_replies_replier_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    review: Mapped[Review] = relationship(back_populates="replies")
    user: Mapped[User] = relationship(back_populates="replies")
