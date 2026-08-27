from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.event import Event
    from app.models.log import Log
    from app.models.notification import Notification
    from app.models.rbac import Role
    from app.models.refresh_token import RefreshToken
    from app.models.review import Reply


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_users"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "roles.id",
            name="fk_users_role_id_roles",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
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

    role: Mapped[Role] = relationship(back_populates="users")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    organized_events: Mapped[list[Event]] = relationship(back_populates="organizer")
    bookings: Mapped[list[Booking]] = relationship(back_populates="user")
    replies: Mapped[list[Reply]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    logs: Mapped[list[Log]] = relationship(back_populates="actor")
