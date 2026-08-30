from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.models.enums import UserRole
from app.schemas.auth import RegistrationRole, validate_password_strength


class UserResponse(BaseModel):
    """Public user information returned by the API."""

    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    """Editable fields for the authenticated User's own profile."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = Field(default=None, max_length=320)
    role: RegistrationRole | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def require_non_null_update(self) -> "UserProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be supplied.")

        if any(
            getattr(self, field_name) is None
            for field_name in self.model_fields_set
        ):
            raise ValueError("Profile fields cannot be null.")

        return self


class PasswordChangeRequest(BaseModel):
    """Passwords required to securely replace the current User's password."""

    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def enforce_password_strength(cls, password: SecretStr) -> SecretStr:
        return validate_password_strength(password)

    @model_validator(mode="after")
    def require_different_password(self) -> "PasswordChangeRequest":
        if (
            self.current_password.get_secret_value()
            == self.new_password.get_secret_value()
        ):
            raise ValueError(
                "The new password must differ from the current password."
            )

        return self
