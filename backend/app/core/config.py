from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
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

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_database_url(cls, v: str) -> str:
        prefix_async = "sqlite+aiosqlite:///"
        prefix_sync = "sqlite:///"
        for prefix in (prefix_async, prefix_sync):
            if v.startswith(prefix):
                raw_path = v[len(prefix):]
                if not Path(raw_path).is_absolute() and not (len(raw_path) > 2 and raw_path[1] == ":"):
                    backend_dir = Path(__file__).resolve().parent.parent.parent
                    abs_path = (backend_dir / raw_path).resolve()
                    return f"{prefix}{abs_path.as_posix()}"
        return v

    # AI Provider Settings ("ollama" or "openai")
    AI_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # OpenAI Settings
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Scraper Settings
    CRAWLER_USER_AGENT: str = "VendorGuardAI-SecurityBot/1.0 (+https://vendorguard.ai)"
    CRAWLER_TIMEOUT_SECONDS: int = 30
    DEFAULT_MONITORING_FREQUENCY_HOURS: int = 24

    # RAG Configuration
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 5
    VECTOR_STORE_TYPE: str = "in_memory"

    # Workflow Checkpoint Persistence Configuration
    CHECKPOINT_DATABASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env", "../backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
