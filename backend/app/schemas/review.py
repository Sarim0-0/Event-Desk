from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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


class ReviewUpdate(BaseModel):
    """Client-provided review fields that may be changed."""

    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(default=None, ge=1, le=5, strict=True)
    comment: str | None = Field(default=None, min_length=1)

    @field_validator("rating")
    @classmethod
    def reject_null_rating(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("rating cannot be null.")
        return value

    @field_validator("comment", mode="before")
    @classmethod
    def trim_update_comment(cls, value: object) -> object:
        if value is None:
            raise ValueError("comment cannot be null.")
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one review field must be supplied.")
        return self


class ReviewResponse(BaseModel):
    """Persisted review information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime
