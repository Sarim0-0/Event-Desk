from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: SecretStr
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout_seconds: float = Field(default=30.0, gt=0)
    database_pool_recycle_seconds: int = Field(default=1800, ge=-1)
    database_command_timeout_seconds: float = Field(default=60.0, gt=0)
    database_application_name: str = "eventdesk"

    @field_validator("database_url")
    @classmethod
    def require_async_postgresql_url(cls, value: SecretStr) -> SecretStr:
        raw_url = value.get_secret_value()
        if not raw_url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the postgresql+asyncpg driver"
            )
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return the URL only where a database client requires it."""

        return self.database_url.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """Load and cache settings once per process."""

    return Settings()
