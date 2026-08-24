from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.bookings.enums import BookingStatus

if TYPE_CHECKING:
    from app.modules.events.models import Event
    from app.modules.notifications.models import Notification
    from app.modules.users.models import User


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "(status = 'confirmed' AND cancelled_at IS NULL) OR "
            "(status = 'cancelled' AND cancelled_at IS NOT NULL)",
            name="status_matches_cancellation_time",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(
            BookingStatus,
            name="booking_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=BookingStatus.CONFIRMED,
        server_default=BookingStatus.CONFIRMED.value,
    )
    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="bookings")
    event: Mapped[Event] = relationship(back_populates="bookings")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="related_booking",
        foreign_keys="Notification.related_booking_id",
    )
