from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.events.enums import EventStatus

if TYPE_CHECKING:
    from app.modules.bookings.models import Booking
    from app.modules.notifications.models import Notification
    from app.modules.reminders.models import Reminder
    from app.modules.reviews.models import Review
    from app.modules.users.models import User


class Category(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    events: Mapped[list[Event]] = relationship(back_populates="category")


class Tag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    event_tags: Mapped[list[EventTag]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events: Mapped[list[Event]] = relationship(
        secondary="event_tags",
        back_populates="tags",
        viewonly=True,
    )


class Event(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("ticket_price >= 0", name="ticket_price_non_negative"),
        CheckConstraint("total_tickets >= 0", name="total_tickets_non_negative"),
        CheckConstraint("tickets_available >= 0", name="tickets_available_non_negative"),
        CheckConstraint(
            "tickets_available <= total_tickets",
            name="tickets_available_within_capacity",
        ),
    )

    organizer_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    event_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ticket_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_available: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(
            EventStatus,
            name="event_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=EventStatus.DRAFT,
        server_default=EventStatus.DRAFT.value,
    )

    organizer: Mapped[User] = relationship(back_populates="organized_events")
    category: Mapped[Category | None] = relationship(back_populates="events")
    event_tags: Mapped[list[EventTag]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary="event_tags",
        back_populates="events",
        viewonly=True,
    )
    bookings: Mapped[list[Booking]] = relationship(back_populates="event")
    reviews: Mapped[list[Review]] = relationship(back_populates="event")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="related_event",
        foreign_keys="Notification.related_event_id",
    )
    reminder: Mapped[Reminder | None] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )


class EventTag(Base):
    __tablename__ = "event_tags"

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    event: Mapped[Event] = relationship(back_populates="event_tags")
    tag: Mapped[Tag] = relationship(back_populates="event_tags")
