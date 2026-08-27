from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ReplyRole


class ReplyCreate(BaseModel):
    """Client-provided information used to reply to a Review."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ReplyResponse(BaseModel):
    """Persisted Reply information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    user_id: UUID
    replier_role: ReplyRole
    body: str
    created_at: datetime
    updated_at: datetime
