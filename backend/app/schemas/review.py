from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    """Client-provided information used to leave a review."""

    model_config = ConfigDict(extra="forbid")

    booking_id: UUID
    rating: int = Field(ge=1, le=5, strict=True)
    comment: str = Field(min_length=1)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ReviewResponse(BaseModel):
    """Persisted review information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime
