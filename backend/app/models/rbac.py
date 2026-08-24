from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_roles"),
        UniqueConstraint("name", name="uq_roles_name"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)

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


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        PrimaryKeyConstraint(name="pk_permissions"),
        UniqueConstraint("key", name="uq_permissions_key"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
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
    __table_args__ = (PrimaryKeyConstraint(name="pk_role_permissions"),)

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "roles.id",
            name="fk_role_permissions_role_id_roles",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "permissions.id",
            name="fk_role_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")
