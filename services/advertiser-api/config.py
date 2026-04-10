"""Configuration management for Advertiser API."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Service
    SERVICE_NAME: str = "advertiser-api"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://acraas:acraas@localhost:5432/acraas"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_POOL_SIZE: int = 20

    # Trino
    TRINO_HOST: str = os.getenv("TRINO_HOST", "localhost")
    TRINO_PORT: int = 8080
    TRINO_CATALOG: str = "iceberg"
    TRINO_SCHEMA: str = "acraas"
    TRINO_USER: str = "acraas"
    TRINO_PASSWORD: str | None = None

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )
    CELERY_TASK_TIMEOUT: int = 3600

    # Security
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "your-super-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600  # 1 hour

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 1000

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
