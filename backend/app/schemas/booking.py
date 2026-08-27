from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookingStatus


class BookingCreate(BaseModel):
    """Client-provided information used to book tickets for an event."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    quantity: int = Field(ge=1, strict=True)


class BookingResponse(BaseModel):
    """Booking information returned after successful creation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_id: UUID
    quantity: int
    status: BookingStatus
    booked_at: datetime
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
