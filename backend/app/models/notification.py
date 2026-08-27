from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.review import Review
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_notifications"),
        CheckConstraint(
            "(CASE WHEN related_booking_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN related_review_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="ck_notifications_at_most_one_related_entity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_booking_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "bookings.id",
            name="fk_notifications_related_booking_id_bookings",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    related_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "reviews.id",
            name="fk_notifications_related_review_id_reviews",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="notifications")
    related_booking: Mapped[Booking | None] = relationship(
        back_populates="notifications",
        foreign_keys=[related_booking_id],
    )
    related_review: Mapped[Review | None] = relationship(
        back_populates="notifications",
        foreign_keys=[related_review_id],
    )
