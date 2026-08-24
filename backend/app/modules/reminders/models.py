from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.events.models import Event


class Reminder(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reminders"

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    event: Mapped[Event] = relationship(back_populates="reminder")
