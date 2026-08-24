from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class Role(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    users: Mapped[list[User]] = relationship(back_populates="role")
    role_permissions: Mapped[list[RolePermission]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
        viewonly=True,
    )


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    role_permissions: Mapped[list[RolePermission]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    roles: Mapped[list[Role]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
        viewonly=True,
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")
