from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)


class RegistrationRole(str, Enum):
    """Roles that a user may choose during public registration."""

    ORGANIZER = "organizer"
    ATTENDEE = "attendee"


class SignUpRequest(BaseModel):
    """Information required to create an organizer or attendee account."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=8, max_length=128)
    role: RegistrationRole

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

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: SecretStr) -> SecretStr:
        raw_password = password.get_secret_value()
        missing_requirements: list[str] = []

        if not any(character.islower() for character in raw_password):
            missing_requirements.append("lowercase letter")
        if not any(character.isupper() for character in raw_password):
            missing_requirements.append("uppercase letter")
        if not any(character.isdigit() for character in raw_password):
            missing_requirements.append("number")
        if not any(
            not character.isalnum() and not character.isspace()
            for character in raw_password
        ):
            missing_requirements.append("special character")

        if missing_requirements:
            requirements = ", ".join(missing_requirements)
            raise ValueError(
                f"Password must contain at least one {requirements}."
            )

        return password


class LoginRequest(BaseModel):
    """Credentials used to authenticate an existing account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class RefreshTokenRequest(BaseModel):
    """Refresh token submitted to obtain a new token pair or log out."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


class AccessTokenResponse(BaseModel):
    """A new access token returned after refreshing authentication."""

    access_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"


class TokenResponse(BaseModel):
    """Access and refresh tokens returned after successful authentication."""

    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"
