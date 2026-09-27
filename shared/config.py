"""Application settings, loaded from environment (.env supported)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: str = "*"

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    temporal_host: str = "localhost:7233"
    storage_path: str = "./data/storage"
    log_dir: str = "./logs"

    model_provider: str = "mock"
    model_name: str = "mock-reasoner"
    model_base_url: str = ""
    model_api_key: str = ""
    model_timeout_seconds: int = 120

    # EcomAutopilot (browser-service) integration
    ecom_autopilot_base_url: str = "http://127.0.0.1:8787"
    ecom_autopilot_token: str = "dev-token"
    ecom_autopilot_timeout_seconds: int = 180

    api_auth_token: str = ""
    api_auth_enabled: bool = False
    workspace_name: str = "default"
    max_workflow_retries: int = 2
    auto_create_tables: bool = True
    seed_demo_data: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def resolved_database_url(self) -> str:
        """Use PostgreSQL when configured, otherwise fall back to local SQLite."""
        if self.database_url:
            return self.database_url
        sqlite_path = PROJECT_ROOT / "data" / "ai_company.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path.as_posix()}"

    def resolve_path(self, raw: str) -> Path:
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def storage_dir(self) -> Path:
        directory = self.resolve_path(self.storage_path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def log_dir_path(self) -> Path:
        directory = self.resolve_path(self.log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
