from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import EventStatus

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_categories"),
        UniqueConstraint("name", name="uq_categories_name"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    events: Mapped[list[Event]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_tags"),
        UniqueConstraint("name", name="uq_tags_name"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

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


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_events"),
        CheckConstraint(
            "ticket_price >= 0",
            name="ck_events_ticket_price_non_negative",
        ),
        CheckConstraint(
            "total_tickets >= 0",
            name="ck_events_total_tickets_non_negative",
        ),
        CheckConstraint(
            "tickets_available >= 0",
            name="ck_events_tickets_available_non_negative",
        ),
        CheckConstraint(
            "tickets_available <= total_tickets",
            name="ck_events_tickets_available_within_capacity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    organizer_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_events_organizer_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "categories.id",
            name="fk_events_category_id_categories",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    event_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ticket_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_available: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(
            EventStatus,
            name="ck_events_event_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=EventStatus.DRAFT,
        server_default=EventStatus.DRAFT.value,
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class EventTag(Base):
    __tablename__ = "event_tags"
    __table_args__ = (PrimaryKeyConstraint(name="pk_event_tags"),)

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "events.id",
            name="fk_event_tags_event_id_events",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "tags.id",
            name="fk_event_tags_tag_id_tags",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    event: Mapped[Event] = relationship(back_populates="event_tags")
    tag: Mapped[Tag] = relationship(back_populates="event_tags")
