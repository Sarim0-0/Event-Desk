from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.bookings.models import Booking
    from app.modules.events.models import Event
    from app.modules.reviews.models import Review
    from app.modules.users.models import User


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN related_event_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN related_booking_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN related_review_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="at_most_one_related_entity",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_booking_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reviews.id", ondelete="SET NULL"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="notifications")
    related_event: Mapped[Event | None] = relationship(
        back_populates="notifications",
        foreign_keys=[related_event_id],
    )
    related_booking: Mapped[Booking | None] = relationship(
        back_populates="notifications",
        foreign_keys=[related_booking_id],
    )
    related_review: Mapped[Review | None] = relationship(
        back_populates="notifications",
        foreign_keys=[related_review_id],
    )
