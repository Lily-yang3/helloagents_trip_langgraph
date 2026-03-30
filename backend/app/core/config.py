"""Application settings and startup validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = BACKEND_ROOT / ".env"
load_dotenv(DEFAULT_ENV, override=False)
load_dotenv(override=False)


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "HelloAgents Trip LangGraph"
    app_version: str = "1.0.0"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_id: str = "gpt-4o-mini"
    llm_timeout: int = 60

    amap_api_key: str = ""
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""

    mock_mode: bool = True

    data_dir: str = "./data"
    checkpoint_db: str = "./data/checkpoints.sqlite"
    checkpointer_mode: str = "memory"
    profile_db: str = "./data/profiles.sqlite"
    trips_db: str = "./data/trips.sqlite"
    session_db: str = "./data/sessions.sqlite"

    @field_validator("debug", "mock_mode", mode="before")
    @classmethod
    def normalize_bool(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        text = str(value).strip().lower()
        truthy = {"1", "true", "yes", "y", "on", "debug", "dev", "development"}
        falsy = {"0", "false", "no", "n", "off", "release", "prod", "production"}
        if text in truthy:
            return True
        if text in falsy:
            return False
        return False

    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_data_dirs(self) -> None:
        data_root = Path(self.data_dir)
        data_root.mkdir(parents=True, exist_ok=True)
        for db_path in [self.checkpoint_db, self.profile_db, self.trips_db, self.session_db]:
            target = Path(db_path)
            if not target.is_absolute():
                target = BACKEND_ROOT / target
            target.parent.mkdir(parents=True, exist_ok=True)


_settings = Settings()


def get_settings() -> Settings:
    return _settings


def validate_settings() -> None:
    """Validate startup critical settings.

    Hard requirements:
    - none in mock mode.
    - AMAP_API_KEY when mock_mode is disabled.

    Soft warnings:
    - missing llm key (graph can still run with heuristic fallback).
    """

    settings = get_settings()
    settings.ensure_data_dirs()

    errors: list[str] = []
    warnings: list[str] = []

    if not settings.mock_mode and not settings.amap_api_key:
        errors.append("AMAP_API_KEY is required when MOCK_MODE=false")

    if not settings.llm_api_key:
        warnings.append("LLM_API_KEY is missing. Falling back to deterministic planner mode.")

    if errors:
        raise ValueError("\n".join(errors))

    if warnings:
        for item in warnings:
            print(f"[config-warning] {item}")


def print_settings() -> None:
    settings = get_settings()
    print("=" * 64)
    print(f"{settings.app_name} v{settings.app_version}")
    print(f"host={settings.host} port={settings.port} mock_mode={settings.mock_mode}")
    print(f"llm_model={settings.llm_model_id} llm_key={'yes' if bool(settings.llm_api_key) else 'no'}")
    print(f"amap_key={'yes' if bool(settings.amap_api_key) else 'no'}")
    print(f"data_dir={settings.data_dir}")
    print(f"checkpointer_mode={settings.checkpointer_mode}")
    print("=" * 64)
