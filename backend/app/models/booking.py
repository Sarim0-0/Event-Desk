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
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import BookingStatus

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.notification import Notification
    from app.models.review import Review
    from app.models.user import User


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_bookings"),
        CheckConstraint(
            "quantity > 0",
            name="ck_bookings_quantity_positive",
        ),
        CheckConstraint(
            "(status = 'confirmed' AND cancelled_at IS NULL) OR "
            "(status = 'cancelled' AND cancelled_at IS NOT NULL)",
            name="ck_bookings_status_matches_cancellation_time",
        ),
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_bookings_user_id_event_id",
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
            name="fk_bookings_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "events.id",
            name="fk_bookings_event_id_events",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(
            BookingStatus,
            name="ck_bookings_booking_status",
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
    user: Mapped[User] = relationship(back_populates="bookings")
    event: Mapped[Event] = relationship(back_populates="bookings")
    review: Mapped[Review | None] = relationship(
        back_populates="booking",
        uselist=False,
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="related_booking",
        foreign_keys="Notification.related_booking_id",
    )
