from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    jwt_secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    scheduler_enabled: bool = True
    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized origins configured as a comma-separated list."""

        return [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
