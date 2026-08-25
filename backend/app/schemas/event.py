from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EventStatus


class EventCreateRequest(BaseModel):
    """Client-provided information used to create an event."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    venue: str = Field(min_length=1, max_length=255)
    event_datetime: datetime
    ticket_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    total_tickets: int = Field(gt=0)
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    status: EventStatus = EventStatus.DRAFT

    @field_validator("title", "venue", mode="before")
    @classmethod
    def normalize_short_text(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("event_datetime")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_datetime must include a timezone offset.")
        return value

    @field_validator("tag_ids")
    @classmethod
    def remove_duplicate_tag_ids(cls, tag_ids: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(tag_ids))

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, value: EventStatus) -> EventStatus:
        if value in {EventStatus.CANCELLED, EventStatus.COMPLETED}:
            raise ValueError(
                "A new event cannot start as cancelled or completed."
            )
        return value


class EventResponse(BaseModel):
    """Event information returned after successful creation."""

    id: UUID
    organizer_id: UUID
    title: str
    description: str
    venue: str
    event_datetime: datetime
    ticket_price: Decimal
    total_tickets: int
    tickets_available: int
    category_id: UUID | None
    tag_ids: list[UUID]
    status: EventStatus
    created_at: datetime
    updated_at: datetime
