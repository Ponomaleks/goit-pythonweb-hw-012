"""Application settings loaded from environment variables."""

import json
import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr as SectretStr

SETTINGS_ENV_FILE = os.getenv("SETTINGS_ENV_FILE", ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "contacts-api"
    app_env: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # JWT / Auth
    jwt_secret_key: str = "dev-secret"  # override in production via .env
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email verification / SMTP (dev defaults for local testing)
    email_from: str = "noreply@example.com"
    smtp_host: str | None = "localhost"
    smtp_port: int | None = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None

    # FastAPI-Mail compatible settings
    mail_server: str | None = None
    mail_port: int | None = None
    mail_username: str = ""
    mail_password: SectretStr = SectretStr("")
    mail_from: str | None = None
    mail_start_tls: bool = True
    mail_ssl_tls: bool = False
    mail_template_folder: str | None = "app/templates/email"
    email_verification_token_expire_hours: int = 48

    # CORS
    cors_allowed_origins: list[str] = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ]

    # Rate limiting (string per slowapi/limits format)
    rate_limit_default: str = "10/minute"
    rate_limit_storage_url: str | None = None  # e.g. redis://user:pass@redis:6379/0

    # Cloudinary (avatar uploads)
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            return cls._clean_list(value)

        if isinstance(value, str):
            stripped = value.strip()

            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return cls._clean_list(parsed)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format for cors_allowed_origins")
                if isinstance(parsed, list):
                    return [
                        str(origin).strip() for origin in parsed if str(origin).strip()
                    ]
            return cls._clean_list(value.split(","))

        raise TypeError(f"Unsupported type: {type(value)}")

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=SETTINGS_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @staticmethod
    def _clean_list(items: Any) -> list[str]:
        return [
            str(item).strip()
            for item in items
            if item is not None and str(item).strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    # Type checkers may treat required BaseSettings fields as __init__ args.
    return Settings()  # type: ignore[call-arg]
