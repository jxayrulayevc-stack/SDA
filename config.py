"""Application configuration. Secrets are read only from the environment/.env."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = Field(alias="BOT_TOKEN")
    admin_ids: str = Field(alias="ADMIN_IDS")
    encryption_key: SecretStr = Field(alias="ENCRYPTION_KEY")
    code_ttl_seconds: int = Field(default=60, alias="CODE_TTL_SECONDS")
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    env_file_path: Path = Field(default=Path(".env"), alias="ENV_FILE")
    steam_time_url: str = Field(alias="STEAM_TIME_URL", default="https://api.steampowered.com/ITwoFactorService/QueryTime/v1/")
    steam_time_sync_interval: int = Field(default=3600, alias="STEAM_TIME_SYNC_INTERVAL")
    code_rate_limit: int = Field(default=10, alias="CODE_RATE_LIMIT")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")
    max_upload_bytes: int = Field(default=100 * 1024, alias="MAX_UPLOAD_BYTES")

    @field_validator("admin_ids")
    @classmethod
    def _validate_admin_ids(cls, value: str) -> str:
        try:
            ids = [int(part.strip()) for part in value.split(",") if part.strip()]
        except ValueError as exc:
            raise ValueError("ADMIN_IDS must contain numeric Telegram IDs") from exc
        if not ids:
            raise ValueError("ADMIN_IDS must contain at least one Telegram ID")
        return ",".join(str(admin_id) for admin_id in ids)

    @property
    def admin_id_set(self) -> frozenset[int]:
        return frozenset(int(part) for part in self.admin_ids.split(",") if part)

    @property
    def bot_token_value(self) -> str:
        return self.bot_token.get_secret_value()

    @property
    def encryption_key_value(self) -> str:
        return self.encryption_key.get_secret_value()


def load_settings() -> Settings:
    """Load settings, respecting ENV_FILE for deployments with data outside git."""
    env_file = Path(os.getenv("ENV_FILE", ".env"))
    return Settings(_env_file=env_file, env_file_path=env_file)
