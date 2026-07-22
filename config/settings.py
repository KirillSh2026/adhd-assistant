from __future__ import annotations

from functools import lru_cache

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.exceptions import ConfigurationError


class AppSettings(BaseSettings):
    adhd_storage_backend: str = "json"
    adhd_notes_path: str = "data/notes.json"
    database_url: str = ""
    adhd_dictate_language: str = "ru-RU"
    # Optional PostgreSQL connection options (e.g., "sslmode=require")
    adhd_postgres_options: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("adhd_storage_backend")
    @classmethod
    def validate_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"json", "postgres"}:
            raise ValueError("ADHD_STORAGE_BACKEND must be either 'json' or 'postgres'")
        return normalized

    @field_validator("adhd_notes_path")
    @classmethod
    def validate_notes_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ADHD_NOTES_PATH cannot be empty")
        return normalized

    @field_validator("adhd_dictate_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ADHD_DICTATE_LANGUAGE cannot be empty")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    try:
        return AppSettings()
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc
