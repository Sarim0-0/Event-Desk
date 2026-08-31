from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookingStatus


BOOKINGS_PER_PAGE = 5


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


class BookingListQuery(BaseModel):
    """Validated page number for listing the current User's Bookings."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)


class PaginatedBookingsResponse(BaseModel):
    """One fixed-size page of the authenticated User's Bookings."""

    items: list[BookingResponse]
    page: int = Field(ge=1)
    page_size: Literal[5] = BOOKINGS_PER_PAGE
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
