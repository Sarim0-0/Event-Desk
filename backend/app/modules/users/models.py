from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.audit.models import Log
    from app.modules.auth.models import RefreshToken
    from app.modules.bookings.models import Booking
    from app.modules.events.models import Event
    from app.modules.notifications.models import Notification
    from app.modules.rbac.models import Role
    from app.modules.reviews.models import Reply, Review


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    role: Mapped[Role] = relationship(back_populates="users")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    organized_events: Mapped[list[Event]] = relationship(back_populates="organizer")
    bookings: Mapped[list[Booking]] = relationship(back_populates="user")
    reviews: Mapped[list[Review]] = relationship(back_populates="user")
    replies: Mapped[list[Reply]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    logs: Mapped[list[Log]] = relationship(back_populates="actor")
