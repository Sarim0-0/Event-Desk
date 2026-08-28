from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import EventStatus


EVENTS_PER_PAGE = 6


class EventCreateRequest(BaseModel):
    """Client-provided information used to create an event."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    venue: str = Field(min_length=1, max_length=255)
    event_datetime: datetime
    ticket_price: Decimal = Field(
        ge=0,
        max_digits=10,
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
    def validate_event_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_datetime must include a timezone offset.")
        if value <= datetime.now(timezone.utc):
            raise ValueError("event_datetime must be in the future.")
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


class EventUpdate(BaseModel):
    """Client-provided Event fields that may be changed."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    venue: str | None = Field(default=None, min_length=1, max_length=255)
    event_datetime: datetime | None = None
    ticket_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    total_tickets: int | None = Field(default=None, gt=0)
    category_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    status: EventStatus | None = None

    @field_validator("title", "venue", mode="before")
    @classmethod
    def normalize_update_short_text(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null.")
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_update_description(cls, value: object) -> object:
        if value is None:
            raise ValueError("description cannot be null.")
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("event_datetime")
    @classmethod
    def validate_update_event_datetime(
        cls,
        value: datetime | None,
    ) -> datetime:
        if value is None:
            raise ValueError("event_datetime cannot be null.")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_datetime must include a timezone offset.")
        if value <= datetime.now(timezone.utc):
            raise ValueError("event_datetime must be in the future.")
        return value

    @field_validator("ticket_price", "total_tickets")
    @classmethod
    def reject_null_number(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null.")
        return value

    @field_validator("tag_ids")
    @classmethod
    def validate_update_tag_ids(
        cls,
        tag_ids: list[UUID] | None,
    ) -> list[UUID]:
        if tag_ids is None:
            raise ValueError("tag_ids cannot be null.")
        return list(dict.fromkeys(tag_ids))

    @field_validator("status")
    @classmethod
    def validate_update_status(
        cls,
        value: EventStatus | None,
    ) -> EventStatus:
        if value is None:
            raise ValueError("status cannot be null.")
        if value not in {EventStatus.DRAFT, EventStatus.PUBLISHED}:
            raise ValueError("An Event can only be edited as draft or published.")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one Event field must be supplied.")
        return self


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


class EventListQuery(BaseModel):
    """Validated pagination and filtering values for Event listing."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)

    @field_validator("tag_ids")
    @classmethod
    def remove_duplicate_filter_tag_ids(
        cls,
        tag_ids: list[UUID],
    ) -> list[UUID]:
        return list(dict.fromkeys(tag_ids))


class PaginatedEventsResponse(BaseModel):
    """One fixed-size page of visible Events and its pagination metadata."""

    items: list[EventResponse]
    page: int = Field(ge=1)
    page_size: Literal[6] = EVENTS_PER_PAGE
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
