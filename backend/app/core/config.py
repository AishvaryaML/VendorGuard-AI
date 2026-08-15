import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "VendorGuard AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev_secret_key_change_in_production_environment_with_strong_secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database Configuration
    POSTGRES_USER: str = "vendorguard"
    POSTGRES_PASSWORD: str = "vendorguard_secure_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vendorguard_db"
    
    # Default to SQLite async for local dev zero-dependency bootstrap, upgradable to PostgreSQL via env
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./vendorguard.db",
        description="Async SQLAlchemy database URL"
    )

    # AI & Scraper Settings
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CRAWLER_USER_AGENT: str = "VendorGuardAI-SecurityBot/1.0 (+https://vendorguard.ai)"
    CRAWLER_TIMEOUT_SECONDS: int = 30
    DEFAULT_MONITORING_FREQUENCY_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
