from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class RefreshToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="revocation_not_before_creation",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
