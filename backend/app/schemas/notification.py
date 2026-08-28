from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType


class NotificationResponse(BaseModel):
    """Persisted Notification data returned to its intended recipient."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: NotificationType
    message: str
    related_booking_id: UUID | None
    related_review_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationsReadAllResponse(BaseModel):
    """Number of unread Notifications changed by a mark-all operation."""

    updated_count: int = Field(ge=0)
